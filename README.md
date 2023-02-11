# emotion-api
## Backend for emotion recognition application

### Description
This repository represents an API for emotion recognition mobile application. Its purpose is to get video file from request and get emotions it different timestamps. 
Also there is a Analize jupyter notebook which has data visualization code to see how people react on a video.

### Run
To run this API do the following steps:
1. install requirements `pip install -r requirements.txt` 
2. in command line type `uvicorn main:app`

By default `question` API key is added to the database. API key is only needed to access admin queries. Normal user does not need an API key to send requests.

### Methods
Admin:

GET
* `/records` to get all the records
* `/records/<video_name>` to get records for specified video name
POST
* `/sql?api_key=<api_key>&sql=<sql>` to run custom sql on the database. Yet there is no query to change API key, but you can run 
`/sql?api_key=question&sql=update%20api_key%20set%20key%3D%27<new_api_key>%27%20where%20id%3D1`
DELETE
* `/video/<video_name>` remove video and all associated records

Anybody:

GET
* `/video/<video_id>` get information about a video by id
* `/video/name/<video_name>` get information about a video by name
POST
* `/video/<video_name>` to add video with specified name to dataset
* `/video/key_frames?video_name=<video_name>&key_start_frame=<key_start_frame>&key_end_frame=<key_end_frame>` changes which part of the video to return 
average emotion upon sending video to an api. Set in seconds
* `/emoion_record_binary` sends video to process by the API. Video file and name should be passed in form multipart by keys 'file' and 'video_name' respectively

### Analysis
Here is a graph for a meme video based on data from ~15 records

![graph](https://github.com/anprowh/emotion-api/raw/main/assets/graph.png)

We can see that there happy emotion rises around second 4. That is the moment when the funny moment of the video is. 
