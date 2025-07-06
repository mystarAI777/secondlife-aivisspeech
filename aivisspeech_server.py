from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import json
import os
import tempfile
import uuid
from datetime import datetime
import base64
import io

app = Flask(__name__)
CORS(app)

# 音声合成の設定
VOICE_MODELS = {
    "japanese_female": "Japanese Female Voice",
    "japanese_male": "Japanese Male Voice",
    "japanese_cute": "Japanese Cute Voice"
}

# 音声ファイルを一時保存するディレクトリ
TEMP_AUDIO_DIR = tempfile.gettempdir()

@app.route('/')
def home():
    return "AivisSpeech Server is running!"

@app.route('/synthesize', methods=['POST'])
def synthesize():
    try:
        data = request.get_json()
        text = data.get('text', '')
        voice = data.get('voice', 'japanese_female')
        
        print(f"[{datetime.now()}] Synthesizing: {text} with voice: {voice}")
        
        # テキストが空の場合はエラー
        if not text:
            return jsonify({"error": "テキストが空です"}), 400
        
        # 音声合成を実行
        audio_url = generate_speech(text, voice)
        
        if audio_url:
            return jsonify({
                "audio_url": audio_url,
                "text": text,
                "voice": voice,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({"error": "音声合成に失敗しました"}), 500
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

def generate_speech(text, voice):
    """音声合成を実行"""
    try:
        # 無料のTTSサービスを使用（gTTS代替）
        audio_data = synthesize_with_free_tts(text, voice)
        
        if audio_data:
            # 一意のファイル名を生成
            file_id = str(uuid.uuid4())
            filename = f"speech_{file_id}.mp3"
            filepath = os.path.join(TEMP_AUDIO_DIR, filename)
            
            # 音声ファイルを保存
            with open(filepath, 'wb') as f:
                f.write(audio_data)
            
            # URLを返す
            audio_url = f"{request.host_url}audio/{file_id}"
            return audio_url
        
        return None
        
    except Exception as e:
        print(f"Speech generation error: {e}")
        return None

def synthesize_with_free_tts(text, voice):
    """無料のTTSサービスで音声合成"""
    try:
        # Method 1: gTTS（Google Text-to-Speech）
        try:
            from gtts import gTTS
            import io
            
            # 日本語で音声合成
            tts = gTTS(text=text, lang='ja', slow=False)
            
            # バイトストリームに保存
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            
            return audio_buffer.read()
            
        except ImportError:
            print("gTTS not available, using alternative method")
        
        # Method 2: VoiceVoxのような無料API（もし利用可能な場合）
        # ここでは簡単なダミー音声を生成
        return generate_dummy_audio(text)
        
    except Exception as e:
        print(f"TTS synthesis error: {e}")
        return None

def generate_dummy_audio(text):
    """ダミー音声データを生成（開発用）"""
    try:
        # 簡単なbeep音を生成
        import struct
        import math
        
        sample_rate = 44100
        duration = min(len(text) * 0.1, 3.0)  # テキスト長に応じた長さ（最大3秒）
        frequency = 440  # A4音程
        
        # sine波を生成
        samples = []
        for i in range(int(sample_rate * duration)):
            t = i / sample_rate
            amplitude = 0.3 * math.sin(2 * math.pi * frequency * t)
            samples.append(int(amplitude * 32767))
        
        # WAVフォーマットでエンコード
        audio_data = b'RIFF'
        audio_data += struct.pack('<I', 36 + len(samples) * 2)
        audio_data += b'WAVE'
        audio_data += b'fmt '
        audio_data += struct.pack('<I', 16)  # fmt chunk size
        audio_data += struct.pack('<H', 1)   # PCM format
        audio_data += struct.pack('<H', 1)   # mono
        audio_data += struct.pack('<I', sample_rate)
        audio_data += struct.pack('<I', sample_rate * 2)
        audio_data += struct.pack('<H', 2)   # bytes per sample
        audio_data += struct.pack('<H', 16)  # bits per sample
        audio_data += b'data'
        audio_data += struct.pack('<I', len(samples) * 2)
        
        for sample in samples:
            audio_data += struct.pack('<h', sample)
        
        return audio_data
        
    except Exception as e:
        print(f"Dummy audio generation error: {e}")
        return None

@app.route('/audio/<file_id>')
def get_audio(file_id):
    """音声ファイルを配信"""
    try:
        filename = f"speech_{file_id}.mp3"
        filepath = os.path.join(TEMP_AUDIO_DIR, filename)
        
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True, download_name=filename)
        else:
            return jsonify({"error": "音声ファイルが見つかりません"}), 404
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/voices')
def get_voices():
    """利用可能な音声一覧を取得"""
    return jsonify(VOICE_MODELS)

@app.route('/health')
def health_check():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

# 定期的に古い音声ファイルを削除
def cleanup_old_files():
    """古い音声ファイルを削除"""
    try:
        import glob
        import time
        
        pattern = os.path.join(TEMP_AUDIO_DIR, "speech_*.mp3")
        now = time.time()
        
        for filepath in glob.glob(pattern):
            if os.path.getctime(filepath) < now - 3600:  # 1時間以上古い
                os.remove(filepath)
                print(f"Deleted old audio file: {filepath}")
    
    except Exception as e:
        print(f"Cleanup error: {e}")

if __name__ == '__main__':
    # 起動時にクリーンアップ
    cleanup_old_files()
    
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)
