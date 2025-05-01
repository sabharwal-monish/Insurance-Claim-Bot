import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.schema import SystemMessage, HumanMessage
from app.db_helper import get_db_connection

load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")

llm = ChatGroq(
    temperature=0.7,
    model_name="llama3-70b-8192",
    api_key=groq_api_key
)

def chat_with_groq(message: str, session_id: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM insurance_sessions WHERE session_id = %s", (session_id,))
        claim_data = cursor.fetchone()
        conn.close()

        messages = [
            SystemMessage(content=f"""
You are an AI assistant helping users file vehicle insurance claims.

Here is what the user has already provided:
- Date & Time: {claim_data.get('date_time_of_incident') or '❌ Missing'}
- Policy Number: {claim_data.get('policy_number') or '❌ Missing'}
- Vehicle Info: {claim_data.get('vehicle_info') or '❌ Missing'}
- Incident Description: {claim_data.get('incident_description') or '❌ Missing'}
- Photo Uploaded: {"✅ Yes" if claim_data.get('photo_uploaded') else "❌ No"}

ONLY ask about fields that are still missing. Never repeat questions.
Once everything is collected (except photo), say: "All details received. Please upload a photo of the damage."
"""),
            HumanMessage(content=message)
        ]

        return llm(messages).content
    except Exception as e:
        print("❌ Error in chat_with_groq:", str(e))
        return "Sorry, something went wrong. Please try again later."
