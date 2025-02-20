import os
from dotenv import load_dotenv
from autogen import GroupChat, GroupChatManager
from AINewsJohnStewart.agents.scout.debriefer import ScoutAgent
from AINewsJohnStewart.agents.satirist.satirist import SatiristAgent
from AINewsJohnStewart.utils.logger import setup_logger

load_dotenv()
logger = setup_logger(__name__)

def main():
    try:
        # Initialize agents
        scout = ScoutAgent()
        satirist = SatiristAgent()

        # Create initial message for the workflow
        initial_message = {
            "role": "user",
            "content": """Please analyze AI news with these parameters:
            - Query: artificial intelligence
            - Max articles: 5
            - Min length: 100 words
            - Exclude domains: clickbait.com, lowquality.ai
            
            Analyze each article for novelty, hype, and absurdity."""
        }

        # Configure group chat
        chat = GroupChat(
            agents=[scout, satirist],
            messages=[initial_message],
            max_round=4,
            speaker_selection_method="round_robin"
        )
        
        # Initialize chat manager
        manager = GroupChatManager(
            groupchat=chat,
            llm_config={
                "config_list": [
                    {
                        "model": "claude-3-sonnet-20240229",
                        "api_key": os.getenv("ANTHROPIC_API_KEY")
                    }
                ],
                "timeout": 45,
                "error_handling": {
                    "max_retries": 2,
                    "retry_delay": 5
                }
            }
        )

        # Initiate the workflow
        manager.initiate_chat(
            manager=scout,
            message=initial_message["content"]
        )

        # Process final results
        if manager.groupchat.messages:
            final_message = manager.groupchat.messages[-1]
            if isinstance(final_message, dict) and "content" in final_message:
                logger.info("Workflow completed successfully")
                logger.info(f"Generated script: {final_message['content']}")
            else:
                logger.warning("No valid script generated in final message")
        else:
            logger.warning("No messages generated in the conversation")
            
    except Exception as e:
        logger.error(f"Workflow error: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main()
    