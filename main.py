import os
import json
import logging
import argparse
from typing import Dict, Any, List
from dotenv import load_dotenv
from agents.goal_creator_agent import get_goal_creator_agent
from agents.rag_agent import get_rag_agent
from agents.investment_specialist_agent import get_investment_specialist_agent
from agents.risk_specialist_agent import get_risk_specialist_agent
from agents.goal_specialist_agent import get_goal_specialist_agent
from agents.voting_coordinator_agent import get_voting_coordinator_agent
from agents.presentation_agent import get_presentation_agent
from agents.feedback_agent import get_feedback_agent


# Load environment variables
load_dotenv(override=True)

# Import autogen
import autogen
from autogen import AssistantAgent, UserProxyAgent

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-3.5-turbo" # Or "gpt-3.5-turbo" for lower cost, "gpt-4-turbo"

config_list = [
        {
            "model": OPENAI_MODEL,
            "api_key": OPENAI_API_KEY,
        }
    ]


def run_investment_advisor(user_input):

    """Run the Investment Strategy Advisor using autogen agents."""
    # Configure autogen


    user_proxy = UserProxyAgent(
        name="User",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=0
    )

    # Step 1: Extract structured goal - Passive Goal Creator pattern
    print("\n[Step 1] Extracting investment goals...")

    goal_creator = get_goal_creator_agent(config_list) #Create goal_creator agent from user input

    # Extract structured goal
    user_proxy.initiate_chat(
        goal_creator, 
        message=user_input
    )

    goal_creator_response = goal_creator.last_message()["content"]

    structured_goal = extract_json_response(goal_creator_response)


    # Step 2: Retrieve investment options - RAG pattern
    print("\n[Step 2] Retrieving investment options...")

    knowledge_file = "investment_knowledge.txt"

    knowledge_path = os.path.join("data", knowledge_file)

    rag_agent = get_rag_agent(config_list,knowledge_path,structured_goal)

     # Get investment options
    user_proxy.initiate_chat(
        rag_agent, 
        message=f"Based on this structured goal, what investment options would you recommend? {json.dumps(structured_goal)}"
    )
    
    rag_response = rag_agent.last_message()["content"]

    investment_options =  extract_json_response(rag_response)

    # Step 3: Voting-Based Cooperation pattern
    print("\n[Step 3] Collecting votes from specialists...")

    # Investment Specialist
    investment_specialist = get_investment_specialist_agent(config_list)

     # Get votes from Investment Specialist
    user_proxy.initiate_chat(
        investment_specialist, 
        message=f"Please evaluate these investment options based on returns and diversification: \nGoal: {json.dumps(structured_goal)}\nOptions: {json.dumps(investment_options)}"
    )
    
    investment_response = investment_specialist.last_message()["content"]

    investment_votes = extract_json_response(investment_response)

     # Risk Specialist
    risk_specialist = get_risk_specialist_agent(config_list)

    # Get votes from Risk Specialist
    user_proxy.initiate_chat(
        risk_specialist, 
        message=f"Please evaluate these investment options based on risk alignment: \nGoal: {json.dumps(structured_goal)}\nOptions: {json.dumps(investment_options)}"
    )
    
    risk_response = risk_specialist.last_message()["content"]

    risk_votes = extract_json_response(risk_response)

    # Goal Specialist
    goal_specialist = get_goal_specialist_agent(config_list)

    # Get votes from Goal Specialist
    user_proxy.initiate_chat(
        goal_specialist, 
        message=f"Please evaluate these investment options based on goal alignment: \nGoal: {json.dumps(structured_goal)}\nOptions: {json.dumps(investment_options)}"
    )
    
    goal_response = goal_specialist.last_message()["content"]

    goal_votes = extract_json_response(goal_response)

    # Step 4: Vote Coordination - Finalize strategy
    print("\n[Step 4] Coordinating votes and generating final strategy...")
    
    voting_coordinator = get_voting_coordinator_agent(config_list)

    # Get final strategy
    user_proxy.initiate_chat(
        voting_coordinator, 
        message=f"""
        Please create a final investment strategy based on the following votes:
        
        Goal: {json.dumps(structured_goal)}
        Options: {json.dumps(investment_options)}
        
        Investment Specialist votes: {json.dumps(investment_votes)}
        Risk Specialist votes: {json.dumps(risk_votes)}
        Goal Specialist votes: {json.dumps(goal_votes)}
        """
    )

    coordinator_response = voting_coordinator.last_message()["content"]

    strategy = extract_json_response(coordinator_response)

    # Step 5: Format the presentation
    print("\n[Step 5] Formatting presentation...")
    
    presentation_agent = get_presentation_agent(config_list)

    # Get formatted presentation
    user_proxy.initiate_chat(
        presentation_agent, 
        message=f"Please format this investment strategy for presentation to the user: {json.dumps(strategy)}"
    )

    presentation = presentation_agent.last_message()["content"]
    
    return {
        "structured_goal": structured_goal,
        "investment_options": investment_options,
        "strategy": strategy,
        "presentation": presentation
    }



def extract_json_response(resonse_string):
    # Extract the JSON object from the response
    try:
        json_start = resonse_string.find('{')
        json_end = resonse_string.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            response = json.loads(resonse_string[json_start:json_end])
            print(f"Structured json response: {json.dumps(response, indent=2)}")
            return response
        else:
            raise ValueError("Failed to extract JSON from response")
    except Exception as e:
        print(f"Error extracting structured response: {e}")
        return None
    

def process_feedback(user_feedback, structured_goal, strategy):
    """Process user feedback on the investment strategy."""
    # Configure autogen
    
    print("\n[Feedback] Processing your feedback...")
    
    # Create the feedback agent - Human Reflection pattern
    feedback_agent = get_feedback_agent(config_list)
    
    user_proxy = UserProxyAgent(
        name="User",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=0
    )
    
    # Process the feedback
    user_proxy.initiate_chat(
        feedback_agent, 
        message=f"""
        Process this feedback on an investment recommendation:
        
        Original Goal: {json.dumps(structured_goal)}
        Recommended Strategy: {json.dumps(strategy)}
        User Feedback: {user_feedback}
        """
    )
    
    feedback_response = feedback_agent.last_message()["content"]

    analysis = extract_json_response(feedback_response)

    return analysis
    


def main():
    print("Welcome to the Investment Strategy Advisor!")
    print("Please describe your investment goals (e.g., 'I want to invest for retirement with low risk').")
    print("Type 'quit' to exit.")

    while True:
            user_input = input("\nYour investment goal: ")
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Thank you for using the Investment Strategy Advisor!")
                break
            
            if user_input.strip():
                try:
                    result = run_investment_advisor(user_input)
                    
                    if result:
                        # Present the results
                        print("\n" + "=" * 80)
                        print(result["presentation"])
                        print("=" * 80)
                        
                        # Ask for feedback
                        feedback = input("\nWhat do you think of this recommendation? ")
                        
                        if feedback.strip():
                            # Process the feedback
                            analysis = process_feedback(
                                feedback,
                                result["structured_goal"],
                                result["strategy"]
                            )
                            
                            print("\nThank you for your feedback! Your preferences have been updated.")
                            print(f"\nFeedback analysis: {analysis['feedback_analysis']}")
                            
                            if analysis.get("risk_adjustment") != "no change":
                                print(f"Risk adjustment: {analysis['risk_adjustment']}")
                            
                            if analysis.get("preference_changes"):
                                print(f"Preference changes: {', '.join(analysis['preference_changes'])}")
                            
                            if analysis.get("strategy_adjustments"):
                                print(f"Strategy adjustments for next time: {', '.join(analysis['strategy_adjustments'])}")
                            
                            print("\nWould you like to see another investment strategy? Please provide a new goal.")
                except Exception as e:
                    print(f"Error processing your request: {e}")
                    print("Please try again with a clearer investment goal.")


if __name__ == "__main__":
    main()


