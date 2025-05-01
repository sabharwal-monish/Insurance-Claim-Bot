from fastapi import APIRouter, UploadFile, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path
from uuid import uuid4
from dotenv import load_dotenv
from app.db_helper import get_db_connection
from app.image_processor import process_image
from app.langchain_helper import chat_with_groq

router = APIRouter()

REQUIRED_FIELDS = [
    "date_time_of_incident",
    "policy_number",
    "vehicle_info",
    "incident_description",
    "photo_uploaded"
]

@router.get("/upload-image/{session_id}")
async def upload_image_form(session_id: str):
    return HTMLResponse(content=f"""
        <html>
            <body>
                <h3>Upload Damage Photo for Session: {session_id}</h3>
                <form action="/upload-image/{session_id}" method="post" enctype="multipart/form-data">
                    <input type="file" name="file" accept="image/*" required><br><br>
                    <input type="submit" value="Upload">
                </form>
            </body>
        </html>
    """)

import re

@router.post("/upload-image/{session_id}")
async def upload_image(session_id: str, file: UploadFile):
    try:
        # 🔐 Sanitize session ID and filename
        safe_session_id = re.sub(r'[^a-zA-Z0-9_-]', '', session_id)
        safe_filename = re.sub(r'[^\w_.-]', '', file.filename)
        uploads_dir = Path("data/uploads")
        uploads_dir.mkdir(parents=True, exist_ok=True)
        file_location = uploads_dir / f"{safe_session_id}_{safe_filename}"

        with open(file_location, "wb") as f:
            f.write(await file.read())

        result = process_image(file_location)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE insurance_sessions SET photo_uploaded = TRUE WHERE session_id = %s", (session_id,))
        conn.commit()
        conn.close()

        return {
            "damage": result,
            "message": "Photo uploaded successfully.",
            "image_url": f"http://localhost:8000/uploads/{file_location.name}"
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/dialogflow-webhook")
async def dialogflow_webhook(request: Request):
    try:
        payload = await request.json()
        session_id = payload.get('session', str(uuid4())).split('/')[-1]
        user_input = payload.get('queryResult', {}).get('queryText', '')
        intent = payload.get('queryResult', {}).get('intent', {}).get('displayName', '')
        parameters = payload.get('queryResult', {}).get('parameters', {})

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM insurance_sessions WHERE session_id = %s", (session_id,))
        session = cursor.fetchone()

        if not session:
            cursor.execute("INSERT INTO insurance_sessions (session_id) VALUES (%s)", (session_id,))
            conn.commit()
            session = {
                "session_id": session_id,
                "date_time_of_incident": None,
                "policy_number": None,
                "vehicle_info": None,
                "incident_description": None,
                "photo_uploaded": False
            }

        if intent == "provide_date_time":
            dt = parameters.get("date-time")
            if dt: session["date_time_of_incident"] = str(dt)

        elif intent == "provide_policy_number":
            policy = parameters.get("policy_number")
            if policy: session["policy_number"] = str(policy)

        elif intent == "provide_vehicle_info":
            vehicle = parameters.get("vehicle_info")
            if vehicle: session["vehicle_info"] = vehicle

        elif intent == "describe_incident":
            session["incident_description"] = user_input

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

        all_text_filled = all(session.get(field) for field in REQUIRED_FIELDS[:-1])

        if all_text_filled and not session["photo_uploaded"]:
            upload_link = f"http://localhost:8000/upload-image/{session_id}"
            return {
                "fulfillmentText": f"""
✅ All required details received.

Please upload a photo of the damage to complete your claim.

Click here to upload: {upload_link}
(If the link isn't clickable, copy and paste it into your browser.)
"""
            }

        if all_text_filled and session["photo_uploaded"]:
            summary = f"""
✅ Claim Summary:
- Date/Time: {session['date_time_of_incident']}
- Policy Number: {session['policy_number']}
- Vehicle Info: {session['vehicle_info']}
- Description: {session['incident_description']}
📸 Photo uploaded.

Thank you! Your claim has been successfully filed.
"""
            cursor.execute("DELETE FROM insurance_sessions WHERE session_id = %s", (session_id,))
            conn.commit()
            return {"fulfillmentText": summary}

        response = chat_with_groq(user_input, session_id)
        return {"fulfillmentText": response}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.get("/test-db")
def test_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        conn.close()
        return {"message": "✅ Connected to MySQL successfully."}
    except Exception as e:
        return {"error": str(e)}
