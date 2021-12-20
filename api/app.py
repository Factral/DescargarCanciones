from flask import Flask, jsonify, request, send_file, after_this_request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from urllib import parse
import urllib.request
from youtubesearchpython import VideosSearch
import yt_dlp
import eyed3
from eyed3.id3.frames import ImageFrame
import time
import subprocess
import os
import zipfile
import random

os.chdir('static')
app = Flask(__name__)
CORS(app)
app.config['JSON_AS_ASCII'] = False
socketio = SocketIO(app, cors_allowed_origins='*', ping_interval=100, ping_timeout=5000)

spotify = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id="c9d53d6622df48ffbec775e99d16af49",
                                                                client_secret="35108ddf5b694f118083b5a76fa705bc"))


def create_link_download_song(data):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': '%(id)s.%(ext)s'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f'https://www.youtube.com/watch?v={data["video_id"]}', download=True)
        filename = ydl.prepare_filename(info).replace('m4a', 'mp3').replace('webm', 'mp3')

    audiofile = eyed3.load(filename)
    if audiofile.tag is None:
        audiofile.initTag()

    urllib.request.urlretrieve(data["metadata"]["cover"], data["video_id"])

    audiofile.tag.images.set(ImageFrame.FRONT_COVER, open(data["video_id"], 'rb').read(), 'image/jpeg')
    audiofile.tag.images.set(3, open(data["video_id"], 'rb').read(), 'image/jpeg')
    audiofile.tag.title = data['metadata']['name']
    audiofile.tag.artist = data['metadata']['artist']
    audiofile.tag.album = data['metadata']['album']
    audiofile.tag.save(version=eyed3.id3.ID3_V2_3)

    os.remove(data["video_id"])
    data["link"] = "https://buscar-canciones.herokuapp.com/v1/file/{}".format(filename)
    data["tamaño"] = "{} mb".format(round(os.path.getsize(filename) / (1024 * 1024), 2))

    return data


@app.route('/v1/file/<string:audio_file_name>')
def return_audio_file(audio_file_name):
    audio_file_name = "".join(x for x in audio_file_name if (x.isalnum() or x in "._- ()"))  # secure the filename
    if audio_file_name.endswith(".mp3") and os.path.isfile(f"{audio_file_name}"):
        audio = eyed3.load(f"{audio_file_name}")
        return send_file(f"./static/{audio_file_name}", mimetype="audio/mp3", as_attachment=True,
                         download_name=f"{audio.tag.title}.mp3")
    else:
        return "error", 400


@app.route('/v1/song')
def songg():
    nombreCancion = request.args.get('name')
    if nombreCancion is None:
        return jsonify({"detail": "Error"}), 400
    print(f"nombreCancion: {nombreCancion}")

    if nombreCancion.startswith("spotify:track:"):
        print(nombreCancion,"hola")
        spotify_song = spotify.track(nombreCancion)
        youtube_song = VideosSearch(spotify_song['name'] + " " + spotify_song['artists'][0]['name'], limit=1).result()
        data = {
        "video_id": youtube_song['result'][0]['id'], "format": "mp3",
        "metadata": {"name": spotify_song['name'], "release_date": spotify_song['album']['release_date'],
                     "artist": spotify_song['artists'][0]['name'], "album": spotify_song['album']['name'],
                     "genre": f"N/A", "number": 0,
                     "cover": spotify_song['album']['images'][0]['url'], "time": spotify_song['duration_ms'],
                     'external_link': spotify_song['external_urls']['spotify']},
        }
    else:
        youtube_song = VideosSearch(nombreCancion, limit=1).result()
        data = {
        "video_id": youtube_song['result'][0]['id'], "format": "mp3",
        "metadata": {"name": youtube_song['result'][0]['title'], "release_date": youtube_song['result'][0]['publishedTime'],
                     "artist": youtube_song['result'][0]['channel']['name'], "album": "N/A",
                     "genre": f"N/A", "number": 0,
                     "cover": f'https://i.ytimg.com/vi/{youtube_song["result"][0]["id"]}/hq720.jpg', "time": youtube_song['result'][0]['duration'],
                     "external_link": f"https://www.youtube.com/watch?v={youtube_song['result'][0]['id']}"},
        }

    if youtube_song is None:
        return jsonify({"detail": "Error"}), 400

    finaldata = create_link_download_song(data)
    return jsonify(finaldata)


@app.route('/v1/playlist')
def main():
    link = request.args.get('link')
    if link is None:
        return jsonify({"detail": "Error"}), 400

    songs = spotify.playlist(link)
    songs = songs['tracks']
    songs_in_playlist = []

    while True:
        for song in songs['items']:
            songs_in_playlist.append({
                'album': song['track']['album']['name'],
                'artist': song['track']['artists'][0]['name'],
                'cover': song['track']['album']['images'][0]['url'],
                'genre': 'N/A',
                'name': song['track']['name'],
                'number': 0,
                'release': song['track']['album']['release_date'],
                'time': song['track']['duration_ms'],
                'external_link': song['track']['external_urls']['spotify']
            })
        if not songs['next']:
            break
        songs = spotify.next(songs)

    return jsonify({'size': len(songs_in_playlist), 'canciones': songs_in_playlist})


@app.route('/v1/search/song')
def main2():
    song = request.args.get('name')
    if song is None:
        return jsonify({"detail": "Error"}), 400

    if song.startswith("https://www.youtube.com/watch?v="):
        idVideo = parse.parse_qs(parse.urlparse(song).query)['v'][0]
        youtube_data = VideosSearch(f'https://www.youtube.com/watch?v={idVideo}', limit=1).result()

        return jsonify({
            'nombre': youtube_data['result'][0]['title'],
            'artista': youtube_data['result'][0]['channel']['name'],
            'uri': youtube_data['result'][0]['title'],
            'cover': f'https://i.ytimg.com/vi/{idVideo}/0.jpg',
            'external_link': f'https://www.youtube.com/watch?v={idVideo}'
        })

    songs = []
    spotify_songs = spotify.search(q=song, type='track', limit=25)
    for key in spotify_songs['tracks']['items']:
        songs.append(
            {'nombre': key['name'],
             'artista': key['artists'][0]['name'],
             'uri': key['uri'],
             'cover': key['album']['images'][0]['url'],
             'external_link': key['external_urls']['spotify']
             }
        )
    return jsonify(songs)


@app.route('/v1/checkfiles')
def main4():
    files = [f for f in os.listdir('.') if os.path.isfile(f)]
    for file in files:
        modified_time = os.path.getmtime(f'{file}')
        if file.endswith(".mp3") and time.time() - modified_time > 420:
            os.remove(f'{file}')
    return jsonify({'files': files}), 200

@app.route('/v1/zip', methods=['POST'])
def main3():
    data = request.get_json()
    if data is None or type(data.get('songs')) is not list:
        return jsonify({"detail": "Error"}), 400

    random_string = ('%06x' % random.randrange(16**6)).upper()
    with zipfile.ZipFile(f'{random_string}.zip', 'w') as zip:
        for song in data['songs']:
            zip.write(f'{song}.mp3', compress_type=zipfile.ZIP_DEFLATED)

    @after_this_request
    def remove_file(response):
        os.remove(f'{random_string}.zip')
        return response
        
    return send_file(f"./static/{random_string}.zip", mimetype="application/zip", as_attachment=True,
                        download_name=f'canciones.zip')


@socketio.on('message')
def handle_message(message):
    songs_send = []
    print(message['playlist'])
    subprocess.Popen(['spotdl', message['playlist'], '-p', '{title}.{ext}'], stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE)
    while len(message['songs']) != len(songs_send):
        for song in message['songs']:
            if song["metadata"]["name"] not in songs_send and os.path.isfile(f'{song["metadata"]["name"]}.mp3'):
                try:
                    audiofile = eyed3.load(f'{song["metadata"]["name"]}.mp3')
                    if audiofile.tag is not None and audiofile.tag.title == song["metadata"]["name"]:

                        data = {
                            "song": {"video_id": 0, "format": "mp3"},
                            "metadata": {"name": song['metadata']['name'], "release_date": song['metadata']['release'],
                                         "artist": song['metadata']['artist'], "album": song['metadata']['album'],
                                         "genre": f"N/A", "number": 0,
                                         "cover": song['metadata']['cover'], "time": 0},
                            'position': song['position'],
                            'link': 'https://buscar-canciones.herokuapp.com/v1/file/' + song['metadata'][
                                'name'] + '.mp3',
                            'external_link': song['metadata']['external_link'],
                            'tamaño': "{} mb".format(
                                round(os.path.getsize(f'{song["metadata"]["name"]}.mp3') / (1024 * 1024), 2))
                        }

                        emit('message_reply', data)
                        songs_send.append(song["metadata"]["name"])
                        socketio.sleep(0.5)
                except Exception:
                    pass
    time.sleep(1)
    emit('disconnect')


if __name__ == "__main__":
    socketio.run(app)
