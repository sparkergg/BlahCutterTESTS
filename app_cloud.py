# BLAHCUTTER ESCRITORIO V2.0
import streamlit as st
import os
import json
import shutil
from streamlit import session_state

# Definir la carpeta temporal y Limpiar la carpeta temporal antes de iniciar la app
temp_folder = "temp_dir"
if not os.path.exists(temp_folder):
    os.makedirs(temp_folder)
if not "reproductor" in session_state:
    for filename in os.listdir(temp_folder):
        file_path = os.path.join(temp_folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"Error al eliminar {file_path}: {e}")


# Función para transcribir el archivo con timestamps formateados
def transcribe_and_format(file_path):
    import assemblyai as aai
    aai.settings.api_key = "f8f649f93a254bb79c44befd87b1fe61"
    config = aai.TranscriptionConfig(speech_model=aai.SpeechModel.best, #language_code="es", 
                                     language_detection=True, speaker_labels=True)
    transcriber = aai.Transcriber(config=config)
    if not file_path:
        return "No se cargó ningún archivo."

    transcript = transcriber.transcribe(file_path)
    transcription_data = []
    full_transcription = ""

    # Función interna para formatear timestamps
    def format_timestamp(seconds):
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        return f"{minutes:02}:{remaining_seconds:02}"

    # Función de limpieza de palabras
    def clean_text(text):
        words_to_remove = ["Zweitausendein", "Ÿousand", "ÿ", "ousand", "zweitausendeinousand", "Ÿ"]
        for word in words_to_remove:
            text = text.replace(word, "")
        return text

    # Itera y estructura transcripción con timestamps formateados
    for utterance in transcript.utterances:
        cleaned_text = clean_text(utterance.text)
        start_time = round(utterance.start / 1000, 2)
        end_time = round(utterance.end / 1000, 2)
        formatted_start = format_timestamp(start_time)
        formatted_end = format_timestamp(end_time)

        transcription_data.append({
            "text": cleaned_text,
            "start": formatted_start,
            "end": formatted_end,
            "speaker": utterance.speaker
        })
        full_transcription += f"[{formatted_start} - {formatted_end}] Speaker {utterance.speaker}: {cleaned_text}\n\n"

    return full_transcription, transcription_data


# Función para buscar texto en la transcripción
def search_in_transcription(search_text, transcription_data):
    if not search_text:
        return []

    search_results = []
    for entry in transcription_data:
        if search_text.lower() in entry["text"].lower():
            search_results.append(entry)

    return search_results


# Función para dar formato al JSON de salida
def format_transcription(transcription):
    formatted = [
        {
            "speaker": entry['speaker'],
            "start": entry['start'],
            "end": entry['end'],
            "text": entry['text']
        }
        for entry in transcription
    ]
    return formatted


# Función para cortar el audio
def cut_audio(file_path, start_time, end_time):
    from pydub import AudioSegment
    audio = AudioSegment.from_file(file_path)

    if isinstance(start_time, str):
        start_minutes, start_seconds = map(int, start_time.split(":"))
        start_time_ms = (start_minutes * 60 + start_seconds) * 1000
    else:
        start_time_ms = start_time * 1000

    if isinstance(end_time, str):
        end_minutes, end_seconds = map(int, end_time.split(":"))
        end_time_ms = (end_minutes * 60 + end_seconds) * 1000
    else:
        end_time_ms = end_time * 1000
    end_time_ms += 750
    cut_audio = audio[start_time_ms:end_time_ms]
    return cut_audio


# Función para cortar el video
def cut_video(file_path, start_time, end_time):
    from moviepy.editor import VideoFileClip

    # Convertir tiempos a segundos si están en formato "MM:SS"
    def convert_to_seconds(time_str):
        if isinstance(time_str, str):
            minutes, seconds = map(int, time_str.split(":"))
            return minutes * 60 + seconds
        return time_str  # Si ya es numérico, devuélvelo tal cual

    # Convertir tiempos de inicio y fin
    start_time = convert_to_seconds(start_time)
    end_time = convert_to_seconds(end_time)

    # Ajustar tiempo final para evitar cortes prematuros
    adjusted_end_time = end_time + 0.75  # Ajuste de 0.5 segundos

    # Crear el clip del video
    video = VideoFileClip(file_path)
    video_clip = video.subclip(start_time, adjusted_end_time)
    return video_clip



# Forzar la eliminación del archivo
def force_delete(file_path):
    try:
        os.remove(file_path)
    except PermissionError:
        print(f"Error: {file_path} está en uso y no se puede eliminar.")
    except Exception as e:
        print(f"Error al eliminar {file_path}: {e}")


# Descargador de videos
def video_downloader(url):
    import yt_dlp as dl
    ydl_opts = {
        'format': 'bv[ext=mp4][vcodec=avc1][filesize<180M]+ba[ext=m4a]/b[ext=mp4][filesize<200M]',
        'outtmpl': os.path.join(temp_folder, 'archivo_trabajado.mp4'),
        'force_overwrites': True
    }

    with dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


# Interfaz de Streamlit
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
username=st.secrets["login"]["user"]
password=st.secrets["login"]["pass"]
st.title("BlahCutter")
st.write("Transcriptor de audio y video")
if not st.session_state.authenticated:
    with st.form("login_form"):
        input_user = st.text_input("Usuario")
        input_password = st.text_input("Contraseña", type="password")
        login_button = st.form_submit_button("Iniciar sesión")

    # Validar las credenciales cuando se presiona el botón en el formulario
    if login_button:
        if input_user == username and input_password == password:
            st.session_state.authenticated = True
            st.success("Acceso concedido")
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")
else:
    video_url = st.text_input("Ingresa la URL de YouTube para descargar el video")
    uploaded_file = st.file_uploader("Carga el archivo multimedia", type=["mp3", "mp4", "wav", "m4a", "ogg", "avi", "mov"])
    if video_url:
        st.write("Descargando el video elegido...")
        temp_file_path = os.path.join(temp_folder, "archivo_trabajado.mp4")
        if "temp_file_path" not in st.session_state:
            video_downloader(video_url)
            st.session_state['temp_file_path']=temp_file_path
            st.session_state['file_name']="archivo_trabajado.mp4"
            st.session_state['is_video'] = temp_file_path
            if "transcription" not in st.session_state:
                st.write("Procesando transcripción...")
                transcription, transcription_data = transcribe_and_format(temp_file_path)
                st.session_state['transcription'] = transcription
                st.session_state['transcription_data'] = transcription_data
            else:
                st.write("Transcripción cargada desde la sesión.")
                transcription = st.session_state['transcription']
                transcription_data = st.session_state['transcription_data']
        st.video(temp_file_path)
        st.session_state['reproductor'] = "reproductor"

    elif uploaded_file:
        temp_file_path = os.path.join("temp_dir", uploaded_file.name)
        st.session_state['temp_file_path'] = temp_file_path
        st.session_state['file_name']=uploaded_file.name
        if not os.path.exists("temp_dir"):
            os.makedirs("temp_dir")
        with open(temp_file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        is_video = uploaded_file.name.endswith(('mp4', '.mov', '.avi'))
        if is_video:
            st.video(temp_file_path)
            st.session_state['is_video'] = temp_file_path
        else:
            st.audio(temp_file_path)
            st.session_state['reproductor'] = "reproductor"
        if "transcription" not in st.session_state:
            st.write("Procesando transcripción...")
            transcription, transcription_data = transcribe_and_format(temp_file_path)
            st.session_state['transcription'] = transcription
            st.session_state['transcription_data'] = transcription_data
        else:
            st.write("Transcripción cargada desde la sesión.")
            transcription = st.session_state['transcription']
            transcription_data = st.session_state['transcription_data']

        # Mostrar transcripción en la aplicación
    if 'transcription' in session_state:
        st.text_area("Transcripción", st.session_state.transcription, height=300)

    # Nombre base sin la extensión
    if 'file_name' in session_state:
        base_name = os.path.splitext(st.session_state.file_name)[0]

        # Descargar transcripción como .txt y .json
        text_col1, text_col2 = st.columns(2)
        with text_col1:
                st.download_button(
                    label="Descargar transcripción como .txt",
                    data=st.session_state.transcription,
                    file_name=f"transcripcion {base_name}.txt",
                    mime="text/plain"
                )
        with text_col2:
            formatted_transcription = format_transcription(st.session_state.transcription_data)
            formatted_json = json.dumps(formatted_transcription, indent=4, ensure_ascii=False)
            st.download_button(
                label="Descargar transcripción como .json",
                data=formatted_json,
                file_name=f"transcripcion {base_name}.json",
                mime="application/json"
            )

        # Barra de busqueda de texto
        search_text = st.text_input("Buscar en la transcripción")
        if st.button("Buscar") or search_text:
            search_results = search_in_transcription(search_text, st.session_state.transcription_data)

            if search_results:
                st.write(f"Resultados para '{search_text}':")
                for result in search_results:
                    st.write(
                        f"[{result['start']} - {result['end']}] Speaker {result['speaker']}: {result['text']}")

                selected_result = search_results[0]

                cut_audio_segment = cut_audio(st.session_state.temp_file_path, selected_result['start'], selected_result['end'])
                cut_audio_path = os.path.join("temp_dir", f"cut_{st.session_state.file_name}")
                cut_audio_segment.export(cut_audio_path, format="mp3")

                audio_col1, audio_col2 = st.columns(2)

                # Descargar fragmento de audio
                audio_col1.download_button(
                label="Descargar fragmento de audio",
                data=open(cut_audio_path, "rb").read(),
                file_name=f"fragmento {base_name}.mp3",
                mime="audio/mp3"
                )

                if st.session_state.is_video:
                    cut_video_segment = cut_video(st.session_state.temp_file_path, selected_result['start'], selected_result['end'])
                    cut_video_path = os.path.join("temp_dir", f"fragmento_{base_name}.mp4")
                    cut_video_segment.write_videofile(cut_video_path, codec="libx264", audio_codec="aac")

                    # Descargar fragmento de video
                    audio_col2.download_button(
                    label="Descargar fragmento de video",
                    data=open(cut_video_path, "rb").read(),
                    file_name=f"fragmento {base_name}.mp4",
                    mime="video/mp4"
                    )

        # Interfaz para seleccionar interlocutor
        speaker_ids = set(entry['speaker'] for entry in st.session_state.transcription_data)
        selected_speaker = st.selectbox("Selecciona un interlocutor", options=["Seleccionar"] + list(speaker_ids))

        if selected_speaker and selected_speaker != "Seleccionar":
            speaker_statements = [entry['text'] for entry in st.session_state.transcription_data if entry['speaker'] == selected_speaker]
            concatenated_text = " ".join(speaker_statements)
            st.text_area(f"Declaraciones concatenadas del interlocutor {selected_speaker}", concatenated_text,
                    height=150)

            # Descargar declaraciones del speaker como .txt y .json
            text_col3, text_col4 = st.columns(2)
            with text_col3:
                st.download_button(
                label="Descargar declaraciones como .txt",
                data=concatenated_text,
                file_name=f"declaraciones {selected_speaker}.txt",
                mime="text/plain"
                )
            with text_col4:
                filtered_transcription = [
                {
                "speaker": entry['speaker'],
                "start": entry['start'],
                "end": entry['end'],
                "text": entry['text']
                }
                for entry in st.session_state.transcription_data if entry['speaker'] == selected_speaker
                ]
                filtered_json = json.dumps(filtered_transcription, indent=4, ensure_ascii=False)
                st.download_button(
                label="Descargar declaraciones como .json",
                data=filtered_json,
                file_name=f"declaraciones {selected_speaker}.json",
                mime="application/json"
                )

            # Generar fragmentos de audio y video para el interlocutor seleccionado
            speaker_audio = cut_audio(st.session_state.temp_file_path, 0, 0)
            speaker_video = None
            for entry in st.session_state.transcription_data:
                if entry['speaker'] == selected_speaker:
                    fragment = cut_audio(st.session_state.temp_file_path, entry['start'], entry['end'])
                    speaker_audio += fragment
                    if st.session_state.is_video:
                        video_fragment = cut_video(st.session_state.temp_file_path, entry['start'], entry['end'])
                        if speaker_video is None:
                            speaker_video = video_fragment
                        else:
                            from moviepy.editor import concatenate_videoclips
                            speaker_video = concatenate_videoclips([speaker_video, video_fragment])

            # Descargar declaraciones como audio
            speaker_audio_path = os.path.join("temp_dir", f"declaraciones_{selected_speaker}.mp3")
            speaker_audio.export(speaker_audio_path, format="mp3")
            media_col1, media_col2 = st.columns(2)
            media_col1.download_button(
            label=f"Descargar declaraciones como audio",
            data=open(speaker_audio_path, "rb").read(),
            file_name=f"declaraciones {selected_speaker}.mp3",
            mime="audio/mp3"
            )

            # Descargar declaraciones como video (si es un video)
            if st.session_state.is_video and speaker_video:
                speaker_video_path = os.path.join("temp_dir", f"declaraciones_{selected_speaker}.mp4")
                speaker_video.write_videofile(speaker_video_path, codec="libx264", audio_codec="aac")
                media_col2.download_button(
                label="Descargar declaraciones como video",
                data=open(speaker_video_path, "rb").read(),
                file_name=f"declaraciones {selected_speaker}.mp4",
                mime="video/mp4"
                )
