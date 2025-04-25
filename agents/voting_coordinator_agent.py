# Import autogen
import autogen
from autogen import AssistantAgent, UserProxyAgent


def get_voting_coordinator_agent(config_list):
    voting_coordinator = AssistantAgent(
        name="VotingCoordinator",
        llm_config={
            "config_list": config_list,
            "temperature": 0.1
        },
        system_message="""You are a financial advisor implementing the Voting-Based Cooperation pattern.
        
        Based on the votes and assessments from the Investment, Risk, and Goal specialists, create a final 
        investment strategy recommendation.
        
        Include:
        1. A descriptive summary of the recommendation
        2. Asset allocation percentages
        3. Specific recommended products
        4. Clear rationale for the recommendation. Also include the rationale for products you didn't chose 
        and the rationale for percentages chosen.
        
        Format your response as a JSON object with the following structure:
        {
            "description": "...",
            "allocation": {
                "asset_class1": percentage,
                "asset_class2": percentage,
                ...
            },
            "products": [
                {"name": "...", "description": "...", "percentage": ...}
            ],
            "rationale": "..."
        }
        """
    )

    return voting_coordinator