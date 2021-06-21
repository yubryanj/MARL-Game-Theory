import numpy as np


class Generator:

    def __init__(self) -> None:
        pass

    def generate_scenario(
        self,
        config,
    ):
        """
        Generates an graph meeting the scenario requirements
        :arg    scenario        game theoretical setting desired
        :arg    config          environment configuration contains haircut multiplier, etc
        """

        scenario = config.get('scenario')
        
        valid_scenarios = [
            'debug',
            'not enough money together',
            'not in default',
            'only agent 0 can rescue',
            'only agent 1 can rescue',
            'both agents can rescue',
            'coordination game',
            'volunteers dilemma'

        ]
        if scenario not in valid_scenarios:
            assert False, f"Scenario must be in {valid_scenarios}"

        if scenario == 'debug':
            return self.debug(config)
        elif scenario == 'not enough money together':
            return self.not_enough_money_together(config)
        elif scenario == 'not in default':
            return self.not_in_default(config)
        elif scenario == 'only agent 0 can rescue':
            return self.only_agent_0_can_rescue(config)
        elif scenario == 'only agent 1 can rescue':
            return self.only_agent_1_can_rescue(config)
        elif scenario == 'both agents can rescue':
            return self.both_agents_can_rescue(config)
        elif scenario == 'coordination game':
            return self.coordination_game(config)
        elif scenario == 'volunteers dilemma':
            raise NotImplementedError('volunteers dilemma')
        

    def debug(
        self,
        config
        ):
        """
        Debugging graph
        In this case, the graphs contains the following situation
            1.  the defaulted bank can be rescued with an collective allocation of 2

        :args   config              config containing common settings for the environment (i.e. haircut)
        :output positions           capital allocation to each entity
        :output adjacency_matrix    debt owed by each entity
        """
        adjacency_matrix = [
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],
            [16.0, 16.0, 0.0]
        ]

        position = [35.0, 35.0, 30.0]
        adjacency_matrix = np.asarray(adjacency_matrix)
        position = np.asarray(position)
        return position, adjacency_matrix


    def not_enough_money_together(
        self,
        config
        ):
        """
        Generator for the case: 'not enough money together'
        In this case, the graphs must satify the following conditions:
            1.  both agent has nonzero capital
            2.  the sum of both agent's capital is less than the amount for 
                a successful rescue
            3.  the debtor can be rescued with a transfer geq the 'rescue amount'

        :args   config              config containing common settings for the environment (i.e. haircut)
        :output positions           capital allocation to each entity
        :output adjacency_matrix    debt owed by each entity
        """

        # retrieve commonly used variables for readability
        rescue_amount       = config.get('rescue_amount')
        n_agents            = config.get('n_agents')
        n_entities          = config.get('n_entities')
        max_system_value    = config.get('max_system_value')

        # If rescue amount is less than 2, than either agent can have 0
        # Which descends to the case of only one can rescue, or neither can rescue.
        assert rescue_amount > 2
        
        generated = False
        while not generated:

            """ Generate positions """

            # Allocate memory
            position = np.zeros(n_entities)

            # Sample an amount less than the rescue amount, but greater than 2
            collective_capital = np.random.randint(2, rescue_amount)

            # Allocate the sampled amount across the agents
            position[:n_agents] = np.random.multinomial(
                collective_capital,
                np.ones(n_agents)/(n_agents),
                size=1
                )[0]

            # Determine the remaining capital in the system
            remaining_capital = max_system_value - position[:n_agents].sum()
            
            # Sample an amount such that the sum capital across all agents
            # is less than the total system value
            position[2] = np.random.randint(remaining_capital)


            """ Generate adjacency matrix """
            # Allocate memory
            adjacency_matrix = np.zeros(shape=(n_entities, n_entities))

            # Compute the amount of debt owed
            debt = position[2]  + rescue_amount
            
            # Allocate the debt across solvent banks
            adjacency_matrix[-1,:n_agents] = np.random.multinomial(
                debt,
                np.ones(n_agents)/(n_agents),
                size=1
            )[0]

            """ Graph Verification """
            # Check if both agents has an incentive to rescue
            # TODO: Check this verification
            # TODO: Include other checks
            if self.verify_adjacency_matrix(config,adjacency_matrix):
                generated = True
            

        return position, adjacency_matrix
        

    def not_in_default(
        self,
        config
        ):
        """
        Generator for the case: 'not in default'
        In this case, the graphs must satify the following conditions:
            1.  the rescue amount must equal 0
            2.  the sum of all agent's capital has to be less than the maximum system value
            3.  the agent which is normally the debtor, is not in default

        :args   config              config containing common settings for the environment (i.e. haircut)
        :output positions           capital allocation to each entity
        :output adjacency_matrix    debt owed by each entity
        """

        # retrieve commonly used variables for readability
        rescue_amount       = config.get('rescue_amount')
        n_agents            = config.get('n_agents')
        n_entities          = config.get('n_entities')
        max_system_value    = config.get('max_system_value')

        # In order to not require a rescue, the rescue amount must equal 0
        assert rescue_amount  == 0
        
        generated = False
        while not generated:

            """ Generate positions """

            # Sample a capitalization for each agent
            position = np.random.multinomial(
                max_system_value,
                np.ones(n_entities)/(n_entities),
                size=1
                )[0]

            """ Generate adjacency matrix """
            # Allocate memory
            adjacency_matrix = np.zeros(shape=(n_entities, n_entities))

            # Compute the amount of debt owed (less than current capitalization)
            debt = np.random.randint(position[2])
            
            # Allocate the debt across solvent banks
            adjacency_matrix[-1,:n_agents] = np.random.multinomial(
                debt,
                np.ones(n_agents)/(n_agents),
                size=1
            )[0]

            """ Graph Verification """
            # Check if both agents has an incentive to rescue
            # TODO: Check this verification
            # TODO: Include other checks
            if self.verify_adjacency_matrix(config,adjacency_matrix):
                generated = True
            
        return position, adjacency_matrix


    def only_agent_0_can_rescue(
        self,
        config
        ):
        """
        Generator for the case: 'only agent 0 can rescue'
        In this case, the graphs must satify the following conditions:
            1.  the rescue amount must be geq 1
            2.  agent 0's capitalization must be geq the rescue amount
            3.  agent 1's capitalization must be less than the rescue amount

        :args   config              config containing common settings for the environment (i.e. haircut)
        :output positions           capital allocation to each entity
        :output adjacency_matrix    debt owed by each entity
        """

        # retrieve commonly used variables for readability
        rescue_amount       = config.get('rescue_amount')
        n_agents            = config.get('n_agents')
        n_entities          = config.get('n_entities')
        max_system_value    = config.get('max_system_value')

        # If rescue amount is less than 1, then it transformers into the 'not in default' case
        assert rescue_amount  >= 1
        
        generated = False
        while not generated:

            """ Generate positions """
            position = np.zeros(n_entities)

            # Sample agent 1's capitalization which has to be less than the rescue amount
            agent_1_capitalization = np.random.randint(rescue_amount)
            position[1] = agent_1_capitalization

            # Distribute the remaining system value to agent 0 and the distressed bank
            remaining_capitalization = max_system_value - agent_1_capitalization
            capitalization = np.random.multinomial(
                remaining_capitalization,
                np.ones(n_entities)/(n_entities),
                size=1
                )[0]

            position[0] = capitalization[0]
            position[2] = capitalization[1]

            """ Generate adjacency matrix """
            # Allocate memory
            adjacency_matrix = np.zeros(shape=(n_entities, n_entities))

            # Compute the amount of debt owed
            debt = position[2]  + rescue_amount
            
            # Allocate the debt across solvent banks
            adjacency_matrix[2,:n_agents] = np.random.multinomial(
                debt,
                np.ones(n_agents)/(n_agents),
                size=1
            )[0]


            """ Graph Verification """
            # Check if both agents has an incentive to rescue
            # TODO: Check this verification
            # TODO: Include other checks
            if self.verify_adjacency_matrix(config,adjacency_matrix):
                generated = True
            
        return position, adjacency_matrix


    def only_agent_1_can_rescue(
        self,
        config
        ):
        """
        Generator for the case: 'only agent 1 can rescue'
        In this case, the graphs must satify the following conditions:
            1.  the rescue amount must be geq 1
            2.  agent 1's capitalization must be geq the rescue amount
            3.  agent 0's capitalization must be less than the rescue amount

        :args   config              config containing common settings for the environment (i.e. haircut)
        :output positions           capital allocation to each entity
        :output adjacency_matrix    debt owed by each entity
        """

        # Generate the case of ' only agent 0 can rescue'
        position, adjacency_matrix = self.only_agent_0_can_rescue(config)

        # Swap the positions of agent 0 and agent 1
        position[0], position[1] = position[1], position[0]
        adjacency_matrix[2,0], adjacency_matrix[2,1] = adjacency_matrix[2,1], adjacency_matrix[2,0]
            
        return position, adjacency_matrix


    def both_agents_can_rescue(
        self,
        config
        ):
        """
        Generator for the case: 'both agents can rescue'
        In this case, the graphs must satify the following conditions:
            1.  both agent has nonzero capital
            2.  each agent's capitalization is greater than the rescue amount
            3.  the rescue amount must be geq 1

        :args   config              config containing common settings for the environment (i.e. haircut)
        :output positions           capital allocation to each entity
        :output adjacency_matrix    debt owed by each entity
        """

        # retrieve commonly used variables for readability
        rescue_amount       = config.get('rescue_amount')
        n_agents            = config.get('n_agents')
        n_entities          = config.get('n_entities')
        max_system_value    = config.get('max_system_value')

        # The rescue amount must be geq to 1 to make sure it does not
        # deteriorate into the case of 'no point in rescuing'
        assert rescue_amount >= 1
        
        generated = False
        while not generated:

            """ Generate positions """
            position_generated = False

            while not position_generated:
                # Same a system amount
                total_capital = np.random.randint(max_system_value)

                # Allocate the sampled amount across the agents
                position = np.random.multinomial(
                    total_capital,
                    np.ones(n_entities)/(n_entities),
                    size=1
                    )[0]
                
                if  position[0] >= rescue_amount and\
                    position[1] >= rescue_amount:
                    position_generated = True

            """ Generate adjacency matrix """
            # Allocate memory
            adjacency_matrix = np.zeros(shape=(n_entities, n_entities))

            # Compute the amount of debt owed
            debt = position[2]  + rescue_amount
            
            # Allocate the debt across solvent banks
            adjacency_matrix[-1,:n_agents] = np.random.multinomial(
                debt,
                np.ones(n_agents)/(n_agents),
                size=1
            )[0]

            """ Graph Verification """
            # Check if both agents has an incentive to rescue
            # TODO: Check this verification
            # TODO: Include other checks
            if self.verify_adjacency_matrix(config,adjacency_matrix):
                generated = True
            

        return position, adjacency_matrix


    def coordination_game(
        self,
        config
        ):
        """
        Generator for the case: 'coordination game'
        In this case, the graphs must satify the following conditions:
            1.  both agent has nonzero capital
            2.  the sum of both agent's capitalization equals the rescue amount
            3.  the rescue amount must be geq 2

        :args   config              config containing common settings for the environment (i.e. haircut)
        :output positions           capital allocation to each entity
        :output adjacency_matrix    debt owed by each entity
        """

        # retrieve commonly used variables for readability
        rescue_amount       = config.get('rescue_amount')
        n_agents            = config.get('n_agents')
        n_entities          = config.get('n_entities')
        max_system_value    = config.get('max_system_value')

        # The rescue amount must be geq to 2 such that each agent contributes at least 1
        assert rescue_amount >= 2
        
        generated = False
        while not generated:

            """ Generate positions """
            position = np.zeros(n_entities)
            
            # Same a system amount
            total_capital = np.random.randint(max_system_value)

            # Allocate the sampled amount across the agents
            position[:n_agents] = np.random.multinomial(
                rescue_amount,
                np.ones(n_agents)/(n_agents),
                size=1
                )[0]
            
            # Allocate the remaining capitalization to the distressed bank
            position[2] = total_capital - position[:n_agents].sum()

            """ Generate adjacency matrix """
            # Allocate memory
            adjacency_matrix = np.zeros(shape=(n_entities, n_entities))

            # Compute the amount of debt owed
            debt = position[2]  + rescue_amount
            
            # Allocate the debt across solvent banks
            adjacency_matrix[-1,:n_agents] = np.random.multinomial(
                debt,
                np.ones(n_agents)/(n_agents),
                size=1
            )[0]

            """ Graph Verification """
            # Check if both agents has an incentive to rescue
            # TODO: Check this verification
            # TODO: Include other checks
            if self.verify_adjacency_matrix(config,adjacency_matrix):
                generated = True
            

        return position, adjacency_matrix



    def verify_adjacency_matrix(
        self,
        config,
        adjacency_matrix
        ):
        """
        Conducts general verifications of the generated adjacency matrix
        :args   config              environment configuration
        :args   adjacency_matrix    adjacency matrix to be verified 
        """
        max_system_value    = config.get('max_system_value')
        n_agents            = config.get('n_agents')

        # Test 1: Assert that each entry is geq 0
        assert (adjacency_matrix>=0).all(), 'There exists an entry in adjacency matrix that is < 0'

        # Test 2: Assert that each entry is less than max system value
        assert (adjacency_matrix<max_system_value).all(), "There exists an entry in the adjacency matrix that is geq the maximum system value"

        # Test 3: Assert that the sum of debts is less than the maximum system value
        # TODO: Is this a valid constraint?  There can be money multiplier effects
        # assert (adjacency_matrix[:n_agents].sum() < max_system_value), "Total debts is greater than the maximum system value"


        return True


if __name__ == "__main__":
    from utils import get_args


    args = get_args()
    config = {
            "n_agents":             2,
            "n_entities":           args.n_agents + 1,
            "haircut_multiplier":   args.haircut_multiplier,
            'discrete':             args.discrete,
            'max_system_value':     args.max_system_value, 
            'debug':                args.debug,
            'number_of_negotiation_rounds':     args.number_of_negotiation_rounds,
            'alpha':                args.alpha,
            'beta':                 args.beta,
        }

    case = 'not in default'

    if case =='debug':
        pass
    elif case == 'not enough money together':
        config['scenario'] = 'not enough money together'
        config['rescue_amount'] = 3
    elif case == 'not in default':
        config['scenario'] = 'not in default'
        config['rescue_amount'] = 0
    elif case == 'only agent 0 can rescue':
        config['scenario'] = 'only agent 0 can rescue'
        config['rescue_amount'] = 2
    elif case == 'only agent 1 can rescue':
        config['scenario'] = 'only agent 1 can rescue'
        config['rescue_amount'] = 2
    elif case == 'both agents can rescue':
        config['scenario'] = 'both agents can rescue'
        config['rescue_amount'] = 2
    elif case == 'coordination game':
        config['scenario'] = 'coordination game'
        config['rescue_amount'] = 2
    elif case == 'volunteers dilemma':
        config['scenario'] = 'volunteers dilemma'
        config['rescue_amount'] = 2
    else:
        assert False
    


    g = Generator()
    adjacency_matrix, position = g.generate_scenario(
        config,
    )

    print(adjacency_matrix)

    print(position)