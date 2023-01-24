from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import sqlite3
from string import ascii_letters, digits
from random import choice
from data_process import video_to_emotions, emotions_to_main_emotion
from fastapi.staticfiles import StaticFiles
import winsound


def generate_api_key():
    return ''.join(choice(ascii_letters + digits) for i in range(16))

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

# Managing CORS

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# db_conn = psycopg2.connect(database="emotion", user="postgres", password=config.psql_password, host="127.0.0.1", port="5432")
db_conn = sqlite3.connect('emotion.db')
db_cursor = db_conn.cursor()

# tables: video, emotion_record, api_key
# video: id, link
# emotion_record: id, video_id, timestamp, angry, disgust, fearf, happy, sad, surprise, neutral, gender (emotions are ratios)
# api_key: id, key
create_video_table = """CREATE TABLE IF NOT EXISTS video (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    link VARCHAR(255) NOT NULL,
    key_start_frame INTEGER DEFAULT 0,
    key_end_frame INTEGER
);"""

create_emotion_record_table = """CREATE TABLE IF NOT EXISTS emotion_record (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    video_id INTEGER NOT NULL,
    timestamp REAL NOT NULL,
    angry REAL NOT NULL,
    disgust REAL NOT NULL,
    fear REAL NOT NULL,
    happy REAL NOT NULL,
    sad REAL NOT NULL,
    surprise REAL NOT NULL,
    neutral REAL NOT NULL,
    gender VARCHAR(1) NOT NULL,

    FOREIGN KEY (video_id) REFERENCES video (id)
);"""

create_api_key_table = """CREATE TABLE IF NOT EXISTS api_key (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    key VARCHAR(16) NOT NULL
);"""

get_emotion_records = """SELECT * FROM emotion_record;"""
get_emotion_records_by_video = """SELECT * FROM emotion_record WHERE video_id = %i;"""
get_video_by_id = """SELECT * FROM video WHERE id = %i;"""
get_video_by_name_sql = """SELECT * FROM video WHERE link = '%s';"""
check_api_key = """SELECT EXISTS(SELECT 1 FROM api_key WHERE key = '%s');"""

# insert data
insert_video = """INSERT INTO video (link) VALUES ('%s');"""
insert_emotion_record = """INSERT INTO emotion_record (video_id, timestamp, angry, disgust, fear, happy, sad, surprise, neutral, gender) VALUES (%i, %f, %f, %f, %f, %f, %f, %f, %f, '%s');"""
insert_api_key = """INSERT INTO api_key (key) VALUES ('%s');"""

# update data
update_video_key_start_frame = """UPDATE video SET key_start_frame = %i WHERE id = %i;"""
update_video_key_end_frame = """UPDATE video SET key_end_frame = %i WHERE id = %i;"""

db_cursor.execute(create_video_table)
db_cursor.execute(create_emotion_record_table)
db_cursor.execute(create_api_key_table)
db_conn.commit()

def check_api(api_key):
    if (not api_key):
        return {"message": "No API key provided"}
    # check for sql injection
    if (not api_key.isalnum()):
        return {"message": "Invalid API key"}
    db_cursor.execute(check_api_key % api_key)
    if (not db_cursor.fetchone()[0]):
        return {"message": "Invalid API key"}
    return {"message": "API key valid"}

# add api key "question" if it doesn't exist
if check_api("question")["message"] != "API key valid":
    db_cursor.execute(insert_api_key % "question")
    db_conn.commit()

# run custom sql
@app.post("/sql")
async def run_sql(api_key: str, sql: str):
    check_api(api_key)

    db_cursor.execute(sql)
    db_conn.commit()
    return db_cursor.fetchall()

@app.get("/")
async def root():
    return {"message": "Hello World"}

# requires api key
@app.get("/records")
async def get_records(api_key: str):
    check_api(api_key)

    db_cursor.execute(get_emotion_records)
    return db_cursor.fetchall()


# requires api key
@app.get("/records/{video_name}")
async def get_records(api_key: str, video_name: str):
    check_api(api_key)

    db_cursor.execute(get_video_by_name_sql % video_name)
    video_id = db_cursor.fetchone()
    if (not video_id):
        return {"message": "Video not found"}
    video_id = video_id[0]
    db_cursor.execute(get_emotion_records_by_video % video_id)
    return db_cursor.fetchall()

@app.get("/video/{video_id}")
async def get_video(video_id: int):
    db_cursor.execute(get_video_by_id % video_id)
    return db_cursor.fetchall()

@app.get("/video/name/{video_name}")
async def get_video_by_name(video_name: str):
    db_cursor.execute(get_video_by_name_sql % video_name)
    return db_cursor.fetchone()

# update video key frames
@app.post("/video/key_frames")
async def post_video_key_frames(video_name: str, key_start_frame: float, key_end_frame: float):
    db_cursor.execute(get_video_by_name_sql % video_name)
    video_id = db_cursor.fetchone()
    if (not video_id):
        return {"message": "Video not found"}
    video_id = video_id[0]
    db_cursor.execute(update_video_key_start_frame % (key_start_frame, video_id))
    db_cursor.execute(update_video_key_end_frame % (key_end_frame, video_id))
    db_conn.commit()
    return {"message": "Video key frames updated"}


# add video "kratos.mp3" if it doesn't exist
if not get_video_by_name("kratos.mp3"):
    db_cursor.execute(insert_video % "kratos.mp3")
    db_conn.commit()

@app.post("/video")
async def post_video(name: str):
    # if video already exists, return
    db_cursor.execute(get_video_by_name_sql % name)
    if (db_cursor.fetchone()):
        return {"message": "Video already exists"}
    db_cursor.execute(insert_video % name)
    db_conn.commit()
    return {"message": f"Video {name} added"}

@app.post("/emotion_record")
async def post_emotion_record(video_name: str, timestamp: int, 
    angry: float, disgust: float, fear: float, happy: float, sad: float, surprise: float, neutral: float, gender: str):
    db_cursor.execute(get_video_by_name_sql % video_name)
    video_id = db_cursor.fetchone()[0]
    db_cursor.execute(insert_emotion_record % (video_id, timestamp, angry, disgust, fear, happy, sad, surprise, neutral, gender))
    db_conn.commit()
    return {"message": "Emotion record added"}


video_index = 0

# emotion record by video binary data
@app.post('/emotion_record_binary')
# async def post_emotion_record_binary(video_name: str, file: bytes = File()):
async def post_emotion_record_binary(request: Request):
    global video_index
    form = await request.form()
    winsound.Beep(440, 300)
    
    video_name = form['video_name']
    
    file = form['file'].file.read()
    with open(f"./out/test{video_index}.mp4", "wb") as f:
        f.write(file)
    video_index += 1
    db_cursor.execute(get_video_by_name_sql % video_name)
    video = db_cursor.fetchone()

    if (not video):
        return {"message": "Video not found"}
    video_id = video[0]
    key_start = video[2]
    key_end = video[3]

    emotions = video_to_emotions(file)
    for timestamp, angry, disgust, fear, happy, sad, surprise, neutral, gender in emotions:
        db_cursor.execute(insert_emotion_record % (video_id, timestamp, angry, disgust, fear, happy, sad, surprise, neutral, gender))
    
    main_emotion, emotion_dict = emotions_to_main_emotion(emotions, start=key_start, end=key_end)

    db_conn.commit()

    return {"message": "Emotion record added", 'main_emotion': main_emotion, 'emotion_dict': emotion_dict}

# clear data for video
@app.delete("/video/{video_name}")
async def delete_video(video_name: str, api_key: str):
    check_api(api_key)

    db_cursor.execute(get_video_by_name_sql % video_name)
    video_id = db_cursor.fetchone()
    if (not video_id):
        return {"message": "Video not found"}
    video_id = video_id[0]

    db_cursor.execute("DELETE FROM emotion_record WHERE video_id = %i;" % video_id)
    db_cursor.execute("DELETE FROM video WHERE id = %i;" % video_id)
    db_conn.commit()
    return {"message": "Video deleted"}

# return kratos video
@app.get("/kratos")
async def get_kratos():
    return FileResponse("./static/kratos.mp4")

# to get video "kratos.mp4" from the server in javascript:
# fetch("http://localhost:8000/static/kratos.mp4").then(response => response.blob()).then(blob => {

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)