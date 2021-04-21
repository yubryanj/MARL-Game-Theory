from ray.rllib.models.torch.torch_modelv2 import TorchModelV2
from ray.rllib.models.modelv2 import ModelV2
from ray.rllib.models.preprocessors import get_preprocessor

from ray.rllib.utils.annotations import override
from ray.rllib.models.torch.misc import SlimFC, AppendBiasLayer, \
    normc_initializer
from ray.rllib.utils.framework import try_import_torch

from ray.rllib.models.torch.fcnet import FullyConnectedNetwork
from gym.spaces import Box
from ray.rllib.utils.torch_ops import FLOAT_MIN, FLOAT_MAX
from ray.rllib.utils.typing import Dict, TensorType, List, ModelConfigDict

import gym
import numpy as np

torch, nn = try_import_torch()


class Custom_Model(TorchModelV2, nn.Module):
    """Torch version of FastModel (tf)."""

    def __init__(self, obs_space, action_space, num_outputs, model_config,
                 name):
        TorchModelV2.__init__(self, obs_space, action_space, num_outputs,
                              model_config, name)
        nn.Module.__init__(self)

        self.obs_size = get_preprocessor(obs_space)(obs_space).size
        self.layer1 = torch.nn.Linear(self.obs_size, 128)
        self.layer2 = torch.nn.Linear(128, 128)
        self.layer3 = torch.nn.Linear(128, 128)
        self.action = torch.nn.Linear(128, num_outputs)
        
        self.value = torch.nn.Linear(self.obs_size, 1)

        self._output = None

    @override(ModelV2)
    def forward(self, input_dict, state, seq_lens):
        self._output = input_dict['obs']
        x = self.layer1(self._output)
        x = self.layer2(x)
        x = self.layer3(x)
        action = self.action(x)

        return action, []

    @override(ModelV2)
    def value_function(self):
        assert self._output is not None, "must call forward first!"
        return torch.reshape(self.value(self._output), [-1])


# class Discrete_action_model(TorchModelV2, nn.Module):

#     def __init__(self,
#                  obs_space,
#                  action_space,
#                  num_outputs,
#                  model_config,
#                  name,
#                  true_obs_shape=(4, ),
#                  **kw):
#         TorchModelV2.__init__(self, obs_space, action_space, num_outputs,
#                                model_config, name, **kw)
#         nn.Module.__init__(self)

#         true_obs_shape = 4

#         self.layer1 = torch.nn.Linear(4, 128)
#         self.layer2 = torch.nn.Linear(128, 128)
#         self.layer3 = torch.nn.Linear(128, 128)
#         self.action = torch.nn.Linear(128, num_outputs)
        
#         self.value = torch.nn.Linear(4, 1)

#         self._output = None


#         # self.action_embed_model = FullyConnectedNetwork(
#         #     Box(-1, 1, shape=true_obs_shape), action_space, num_outputs,
#         #     model_config, name + "_action_embed")

#     def forward(self, input_dict, state, seq_lens):
#         # Extract the available actions tensor from the observation.
#         action_mask = input_dict["obs"]["action_mask"]

#         # Compute the predicted action embedding
#         # action_embed, _ = self.action_embed_model({"obs": input_dict["obs"]["real_obs"]})


#         self._output = input_dict['obs']['real_obs']
#         x = self.layer1(self._output)
#         x = self.layer2(x)
#         x = self.layer3(x)
#         action = self.action(x)

#         inf_mask = torch.clamp(torch.log(action_mask),FLOAT_MIN, FLOAT_MAX)

#         action_logits = action + inf_mask
        
#         return action_logits, state

#     def value_function(self):
#         return torch.reshape(self.value(self._output), [-1])

#         # return self.action_embed_model.value_function()

class Discrete_action_model(TorchModelV2):

    def __init__(self, obs_space: gym.spaces.Space,
                 action_space: gym.spaces.Space, num_outputs: int,
                 model_config: ModelConfigDict, name: str):
        TorchModelV2.__init__(self, obs_space, action_space, num_outputs,
                              model_config, name)
        nn.Module.__init__(self)

        activation = model_config.get("fcnet_activation")
        hiddens = model_config.get("fcnet_hiddens", [])
        no_final_linear = model_config.get("no_final_linear")
        self.vf_share_layers = model_config.get("vf_share_layers")
        self.free_log_std = model_config.get("free_log_std")

        # Generate free-floating bias variables for the second half of
        # the outputs.
        if self.free_log_std:
            assert num_outputs % 2 == 0, (
                "num_outputs must be divisible by two", num_outputs)
            num_outputs = num_outputs // 2

        layers = []
        # prev_layer_size = int(np.product(obs_space.shape))
        prev_layer_size = int(np.product(obs_space.original_space.spaces.get('real_obs').shape))
        self._logits = None

        # Create layers 0 to second-last.
        for size in hiddens[:-1]:
            layers.append(
                SlimFC(
                    in_size=prev_layer_size,
                    out_size=size,
                    initializer=normc_initializer(1.0),
                    activation_fn=activation))
            prev_layer_size = size

        # The last layer is adjusted to be of size num_outputs, but it's a
        # layer with activation.
        if no_final_linear and num_outputs:
            layers.append(
                SlimFC(
                    in_size=prev_layer_size,
                    out_size=num_outputs,
                    initializer=normc_initializer(1.0),
                    activation_fn=activation))
            prev_layer_size = num_outputs
        # Finish the layers with the provided sizes (`hiddens`), plus -
        # iff num_outputs > 0 - a last linear layer of size num_outputs.
        else:
            if len(hiddens) > 0:
                layers.append(
                    SlimFC(
                        in_size=prev_layer_size,
                        out_size=hiddens[-1],
                        initializer=normc_initializer(1.0),
                        activation_fn=activation))
                prev_layer_size = hiddens[-1]
            if num_outputs:
                self._logits = SlimFC(
                    in_size=prev_layer_size,
                    out_size=num_outputs,
                    initializer=normc_initializer(0.01),
                    activation_fn=None)
            else:
                self.num_outputs = (
                    [int(np.product(obs_space.shape))] + hiddens[-1:])[-1]

        # Layer to add the log std vars to the state-dependent means.
        if self.free_log_std and self._logits:
            self._append_free_log_std = AppendBiasLayer(num_outputs)

        self._hidden_layers = nn.Sequential(*layers)

        self._value_branch_separate = None
        if not self.vf_share_layers:
            # Build a parallel set of hidden layers for the value net.
            prev_vf_layer_size = int(np.product(obs_space.shape))
            vf_layers = []
            for size in hiddens:
                vf_layers.append(
                    SlimFC(
                        in_size=prev_vf_layer_size,
                        out_size=size,
                        activation_fn=activation,
                        initializer=normc_initializer(1.0)))
                prev_vf_layer_size = size
            self._value_branch_separate = nn.Sequential(*vf_layers)

        self._value_branch = SlimFC(
            in_size=prev_layer_size,
            out_size=1,
            initializer=normc_initializer(1.0),
            activation_fn=None)
        # Holds the current "base" output (before logits layer).
        self._features = None
        # Holds the last input, in case value branch is separate.
        self._last_flat_in = None

    @override(TorchModelV2)
    def forward(self, input_dict: Dict[str, TensorType],
                state: List[TensorType],
                seq_lens: TensorType) -> (TensorType, List[TensorType]):

        # Get observations and compute the logits
        obs = input_dict.get('obs').get('real_obs').float()
        self._last_flat_in = obs.reshape(obs.shape[0], -1)
        self._features = self._hidden_layers(self._last_flat_in)
        logits = self._logits(self._features) if self._logits else \
            self._features
        if self.free_log_std:
            logits = self._append_free_log_std(logits)

        # Compute the masks
        action_mask = input_dict.get('obs').get('action_mask')
        inf_mask = torch.clamp(torch.log(action_mask),FLOAT_MIN, FLOAT_MAX)

        # Apply the masks
        logits = logits + inf_mask
        
        return logits, state

    @override(TorchModelV2)
    def value_function(self) -> TensorType:
        assert self._features is not None, "must call forward() first"
        if self._value_branch_separate:
            return self._value_branch(
                self._value_branch_separate(self._last_flat_in)).squeeze(1)
        else:
            return self._value_branch(self._features).squeeze(1)
