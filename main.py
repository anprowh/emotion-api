from fastapi import FastAPI, File
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import psycopg2
import config
from string import ascii_letters, digits
from random import choice
from data_process import video_to_emotions


def generate_api_key():
    return ''.join(choice(ascii_letters + digits) for i in range(16))

app = FastAPI()

# Managing CORS

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

db_conn = psycopg2.connect(database="emotion", user="postgres", password=config.psql_password, host="127.0.0.1", port="5432")
db_cursor = db_conn.cursor()

# tables: video, emotion_record, api_key
# video: id, link
# emotion_record: id, video_id, timestamp, angry, disgust, fearf, happy, sad, surprise, neutral, gender (emotions are ratios)
# api_key: id, key
create_video_table = """CREATE TABLE IF NOT EXISTS video (
    id SERIAL PRIMARY KEY,

    link VARCHAR(255) NOT NULL
);"""

create_emotion_record_table = """CREATE TABLE IF NOT EXISTS emotion_record (
    id SERIAL PRIMARY KEY,

    video_id INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
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
    id SERIAL PRIMARY KEY,
    
    key VARCHAR(16) NOT NULL
);"""

# insert test data
insert_test_video = """INSERT INTO video (link) VALUES ('9bZkp7q19f0');"""
insert_test_emotion_record = """INSERT INTO emotion_record (video_id, timestamp, angry, disgust, fear, happy, sad, surprise, neutral, gender) VALUES (1, 0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 'M');"""

get_emotion_records = """SELECT * FROM emotion_record;"""
get_emotion_records_by_video = """SELECT * FROM emotion_record WHERE video_id = %i;"""
get_video_by_id = """SELECT * FROM video WHERE id = %i;"""
get_video_by_name_sql = """SELECT * FROM video WHERE link = '%s';"""
check_api_key = """SELECT EXISTS(SELECT 1 FROM api_key WHERE key = '%s');"""

# insert data
insert_video = """INSERT INTO video (link) VALUES ('%s');"""
insert_emotion_record = """INSERT INTO emotion_record (video_id, timestamp, angry, disgust, fear, happy, sad, surprise, neutral, gender) VALUES (%i, %i, %f, %f, %f, %f, %f, %f, %f, '%s');"""
insert_api_key = """INSERT INTO api_key (key) VALUES ('%s');"""

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

# @app.post("/api_key")
# async def post_api_key():
#     api_key = generate_api_key()
#     db_cursor.execute(insert_api_key % api_key)
#     db_conn.commit()
#     return api_key

@app.post("/video")
async def post_video(name: str):
    # if video already exists, return
    db_cursor.execute(get_video_by_name_sql % name)
    if (db_cursor.fetchone()):
        return {"message": "Video already exists"}
    db_cursor.execute(insert_video % name)
    db_conn.commit()
    return {"message": "Video added"}

@app.post("/emotion_record")
async def post_emotion_record(video_name: str, timestamp: int, 
    angry: float, disgust: float, fear: float, happy: float, sad: float, surprise: float, neutral: float, gender: str):
    db_cursor.execute(get_video_by_name_sql % video_name)
    video_id = db_cursor.fetchone()[0]
    db_cursor.execute(insert_emotion_record % (video_id, timestamp, angry, disgust, fear, happy, sad, surprise, neutral, gender))
    db_conn.commit()
    return {"message": "Emotion record added"}

# emotion record by video binary data
@app.post('/emotion_record_binary')
async def post_emotion_record_binary(video_name: str, file: bytes = File()):
    print(len(file))
    db_cursor.execute(get_video_by_name_sql % video_name)
    video_id = db_cursor.fetchone()

    if (not video_id):
        return {"message": "Video not found"}
    video_id = video_id[0]

    emotions = video_to_emotions(file)
    for timestamp, angry, disgust, fear, happy, sad, surprise, neutral, gender in emotions:
        db_cursor.execute(insert_emotion_record % (video_id, timestamp, angry, disgust, fear, happy, sad, surprise, neutral, gender))
    
    db_conn.commit()
    return emotions

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


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)