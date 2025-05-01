from fastapi import FastAPI, UploadFile, Request
from fastapi.responses import JSONResponse
from uuid import uuid4
from PIL import Image
from dotenv import load_dotenv
import os
from langchain_groq import ChatGroq
from langchain.schema import SystemMessage, HumanMessage
from app.db_helper import get_db_connection  

app = FastAPI()

# --- REQUIRED FIELDS ---
REQUIRED_FIELDS = [
    "date_time_of_incident",
    "policy_number",
    "vehicle_info",
    "incident_description",
    "photo_uploaded"
]

# --- IMAGE PROCESSING ---
def process_image(image_path):
    image = Image.open(image_path)
    return "Car Damage Detected"

@app.post('/upload-image/{session_id}')
async def upload_image(session_id: str, file: UploadFile):
    try:
        file_location = f'temp_image_{session_id}.jpg'
        with open(file_location, 'wb') as f:
            f.write(await file.read())

        result = process_image(file_location)

        # ✅ Update photo_uploaded in the DB
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE insurance_sessions
            SET photo_uploaded = TRUE
            WHERE session_id = %s
        """, (session_id,))
        conn.commit()
        conn.close()

        return {'damage': result, 'message': 'Photo uploaded successfully.'}
    except Exception as e:
        print("❌ Error in upload_image:", str(e))
        return JSONResponse(status_code=500, content={"error": str(e)})

# --- CHATBOT SETUP ---
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

        missing = [field for field in REQUIRED_FIELDS if not claim_data.get(field)]

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


        response = llm(messages).content
        return response
    except Exception as e:
        print("❌ Error in chat_with_groq:", str(e))
        return "Sorry, something went wrong. Please try again later."

# --- DIALOGFLOW WEBHOOK ---
@app.post("/dialogflow-webhook")
async def dialogflow_webhook(request: Request):
    try:
        payload = await request.json()
        print(f"📌 Raw session string: {payload.get('session')}")
        session_id = payload.get('session', str(uuid4())).split('/')[-1]
        user_input = payload.get('queryResult', {}).get('queryText', '')
        intent = payload.get('queryResult', {}).get('intent', {}).get('displayName', '')
        parameters = payload.get('queryResult', {}).get('parameters', {})

        print(f"🤖 Intent: {intent}, Parameters: {parameters}")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Check if session exists
        cursor.execute("SELECT * FROM insurance_sessions WHERE session_id = %s", (session_id,))
        session = cursor.fetchone()

        if not session:
            # Create new session
            cursor.execute("""
                INSERT INTO insurance_sessions (session_id) VALUES (%s)
            """, (session_id,))
            conn.commit()
            session = {
                "session_id": session_id,
                "date_time_of_incident": None,
                "policy_number": None,
                "vehicle_info": None,
                "incident_description": None,
                "photo_uploaded": False
            }

        # Update session fields
        if intent == "provide_date_time":
            dt = parameters.get("date-time")
            if dt:
                session["date_time_of_incident"] = str(dt)

        elif intent == "provide_policy_number":
            policy = parameters.get("policy_number")
            if policy:
                session["policy_number"] = str(policy)

        elif intent == "provide_vehicle_info":
            vehicle = parameters.get("vehicle_info")
            if vehicle:
                session["vehicle_info"] = vehicle

        elif intent == "describe_incident":
            session["incident_description"] = user_input

        # Update session in DB
        cursor.execute("""
            UPDATE insurance_sessions
            SET date_time_of_incident = %s,
                policy_number = %s,
                vehicle_info = %s,
                incident_description = %s,
                photo_uploaded = %s
            WHERE session_id = %s
        """, (
            session["date_time_of_incident"],
            session["policy_number"],
            session["vehicle_info"],
            session["incident_description"],
            session["photo_uploaded"],
            session_id
        ))
        conn.commit()

        # Check if all required text fields are filled
        all_text_filled = all(session.get(field) for field in [
            "date_time_of_incident",
            "policy_number",
            "vehicle_info",
            "incident_description"
        ])

        if all_text_filled and not session["photo_uploaded"]:
            return {"fulfillmentText": "All details received. Please upload a photo of the damage to complete your claim. You can do so now."}

        if all_text_filled and session["photo_uploaded"]:
            summary = f"""
✅ Claim Summary:
- Date/Time: {session['date_time_of_incident']}
- Policy Number: {session['policy_number']}
- Vehicle Info: {session['vehicle_info']}
- Description: {session['incident_description']}

Thank you! Your claim has been successfully filed.
"""
            cursor.execute("DELETE FROM insurance_sessions WHERE session_id = %s", (session_id,))
            conn.commit()
            return {"fulfillmentText": summary}

        # Otherwise, ask for missing info
        response = chat_with_groq(user_input, session_id)
        return {"fulfillmentText": response}

    except Exception as e:
        print("❌ Error:", str(e))
        return JSONResponse(status_code=500, content={"error": str(e)})

# --- TEST CONNECTION ---
@app.get("/test-db")
def test_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        conn.close()
        return {"message": "✅ Connected to the MySQL database successfully."}
    except Exception as e:
        return {"error": str(e)}
