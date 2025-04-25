# Import autogen
import autogen
from autogen import AssistantAgent, UserProxyAgent


def get_risk_specialist_agent(config_list):
    # Risk Specialist
    risk_specialist = AssistantAgent(
        name="RiskSpecialist",
        llm_config={
            "config_list": config_list,
            "temperature": 0.2
        },
        system_message="""You are a risk assessment specialist focusing on investment volatility and risk profiles.
        
        Evaluate investment options based solely on their risk profiles and how well they align with the 
        user's stated risk tolerance. Focus especially on potential downside risks.
        
        Your evaluation should result in a vote on each product with a score from 1-10 
        (10 being perfect alignment with the user's risk tolerance).
        
        Also provide a brief rationale for your votes.
        
        Format your response as a JSON object with the following structure:
        {
            "product_votes": [
                {"product_name": "...", "score": X, "rationale": "..."}
            ],
            "overall_assessment": "..."
        }
        """
    )

    return risk_specialist