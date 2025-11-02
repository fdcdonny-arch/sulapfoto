import streamlit as st
import requests
import base64
import json
import io

# --- Konfigurasi API ---
# Gunakan st.secrets untuk menyimpan kunci API Anda dengan aman (Streamlit Secrets)
# Pastikan Anda sudah menambahkan [secrets.toml] dengan:
# gemini_api_key = "KUNCI_API_ANDA_DI_SINI"
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    # Fallback untuk testing lokal, TIDAK DIREKOMENDASIKAN untuk deployment
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    if not API_KEY:
        st.error("🔑 Kunci API Gemini tidak ditemukan. Harap simpan kunci Anda di Streamlit Secrets.")

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image-preview:generateContent"
MODEL_NAME = "gemini-2.5-flash-image-preview"

# --- Prompts Kualitas Tinggi untuk Keluaran Resolusi Tinggi ---
QUALITY_ENHANCEMENT = ", very high resolution, 8K, cinematic lighting, photorealistic, hyper-detailed"

# --- Definisi Preset Prompt ---
PRESETS = {
    "👶 Gaya Santai Baby": (
        "Gunakan wajah pada foto yang di upload ini, pertahankan detail wajah dari foto asli. "
        "menjadi bayi baru lahir sedang tidur dengan damai di atas sofa mini berwarna cokelat, "
        "mengenakan baju rajut lembut berwarna biru muda dengan tudung yang memiliki telinga beruang kecil. "
        "Bayi itu bersandar di atas bantal lembut berwarna krem. "
        "Di sekeliling sofa terdapat beberapa boneka beruang dengan ukuran dan warna berbeda (cokelat, abu-abu, oranye). "
        "Latar belakang berupa dinding dan lantai kayu yang hangat, dengan pencahayaan lembut dan hangat khas foto studio bayi. "
        "Sebuah tanaman hijau kecil di pot hitam diletakkan di samping sofa untuk menambah kesan alami dan hangat."
    ),
    "👶 Adat Jawa Baby": (
        "Gunakan wajah pada foto yang di upload ini, pertahankan detail wajah dari foto asli. "
        "menjadi bayi baru lahir sedang tidur dengan damai di atas kursi kecil berwarna abu-abu lembut yang dilapisi kain bertekstur titik-titik putih. "
        "Bayi mengenakan pakaian tradisional Jawa lengkap dengan blangkon hitam bermotif batik merah-oranye di kepala, "
        "baju lurik hijau-cokelat bergaris, dan kain batik cokelat bermotif klasik. "
        "Di pangkuannya terdapat replika kecil keris berwarna emas. "
        "Di samping kursi ada meja bundar kayu kecil dengan sarang burung berisi beberapa telur kecil. "
        "Latar belakang berwarna cokelat lembut dengan nuansa hangat, pencahayaan lembut gaya studio bayi profesional."
    )
}

# --- Fungsi Inti untuk Memanggil API ---
def generate_image(image_bytes, mime_type, user_prompt):
    """
    Memanggil API Gemini untuk menghasilkan gambar yang diedit.
    """
    full_prompt = f"Edit the existing image. Apply the following modification: {user_prompt}. Also, ensure the output image is rendered with{QUALITY_ENHANCEMENT}."
    
    # Konversi byte gambar menjadi string base64
    base64_image = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "contents": [{
            "parts": [
                {"text": full_prompt},
                {
                    "inlineData": {
                        "mimeType": mime_type,
                        "data": base64_image
                    }
                }
            ]
        }],
        "generationConfig": {
            "responseModalities": ["IMAGE"]
        },
    }

    try:
        response = requests.post(f"{API_URL}?key={API_KEY}", json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        
        # Ekstrak data base64 gambar hasil
        base64_data = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('inlineData', {}).get('data')
        
        if base64_data:
            # Mengembalikan byte gambar baru
            return base64.b64decode(base64_data)
        else:
            st.error("Gagal mendapatkan gambar hasil AI. Coba deskripsi yang lain.")
            st.json(result) # Tampilkan respons untuk debugging
            return None

    except requests.exceptions.RequestException as e:
        st.error(f"Terjadi kesalahan saat menghubungi API Gemini: {e}")
        return None

# --- UI Streamlit ---

st.set_page_config(
    page_title="Sulap Foto",
    page_icon="✨",
    layout="centered"
)

st.title("✨ Sulap Foto")
st.markdown("Ubah gaya, pakaian, dan latar belakang foto Anda (*Model: {}*).".format(MODEL_NAME))

# Inisialisasi state untuk menyimpan prompt input
if 'current_prompt' not in st.session_state:
    st.session_state.current_prompt = ""
if 'generated_image_bytes' not in st.session_state:
    st.session_state.generated_image_bytes = None

# 1. Unggah Gambar
uploaded_file = st.file_uploader(
    "Pilih Foto Anda", 
    type=["jpg", "jpeg", "png", "webp"],
    help="Unggah gambar yang ingin Anda edit."
)

# 2. Preset Prompts
st.subheader("💡 Pilih Preset Cepat")

# Buat fungsi callback untuk tombol preset
def set_prompt(preset_key):
    st.session_state.current_prompt = PRESETS[preset_key]
    st.info(f"Preset '{preset_key}' diterapkan! Tekan 'Ubah dengan AI' di bawah.")

cols = st.columns(len(PRESETS))
for i, (key, value) in enumerate(PRESETS.items()):
    with cols[i]:
        if st.button(key, use_container_width=True, disabled=not uploaded_file, help=value):
            set_prompt(key)

# 3. Input Prompt Manual
st.subheader("✍️ Atau Masukkan Deskripsi Anda")
prompt_input = st.text_input(
    "Deskripsi Perubahan (Contoh: 'Ubah latar belakang menjadi galaksi')",
    value=st.session_state.current_prompt,
    key="prompt_manual",
    disabled=not uploaded_file
)
st.session_state.current_prompt = prompt_input # Update state dengan input manual

# --- Tampilkan Gambar yang Diunggah dan Hasil ---
st.subheader("🖼️ Hasil Gambar")
image_placeholder = st.empty()

if uploaded_file is None:
    image_placeholder.image("https://placehold.co/800x400/9ca3af/ffffff?text=Unggah+Foto+di+Sini", caption="Unggah Foto Anda di sini", use_column_width=True)
    st.warning("⚠️ Silakan unggah gambar terlebih dahulu.")
else:
    # Tampilkan gambar yang diunggah
    image_placeholder.image(uploaded_file, caption="Gambar Asli", use_column_width=True)
    
    # 4. Tombol Generate
    if st.button("🚀 Ubah dengan AI", use_container_width=True, disabled=not (uploaded_file and st.session_state.current_prompt)):
        if not API_KEY:
            st.error("🔑 Gagal. Kunci API tidak tersedia.")
        else:
            with st.spinner('⏳ AI sedang bekerja... Mohon tunggu.'):
                
                # Baca byte dan mime_type dari file yang diunggah Streamlit
                image_bytes = uploaded_file.getvalue()
                mime_type = uploaded_file.type
                
                # Panggil fungsi generate_image
                new_image_bytes = generate_image(
                    image_bytes, 
                    mime_type, 
                    st.session_state.current_prompt
                )
                
                if new_image_bytes:
                    st.session_state.generated_image_bytes = new_image_bytes
                    # Tampilkan gambar baru
                    st.success("✅ Gambar berhasil diubah!")
                    image_placeholder.image(new_image_bytes, caption="Gambar Hasil AI", use_column_width=True)
                else:
                    st.session_state.generated_image_bytes = None


# 5. Tombol Download
if st.session_state.generated_image_bytes:
    # Menggunakan st.download_button untuk mengunduh gambar yang dihasilkan
    st.download_button(
        label="⬇️ Unduh Gambar Hasil AI",
        data=st.session_state.generated_image_bytes,
        file_name="sulap-foto-ai-hasil.png",
        mime="image/png",
        use_container_width=True
    )
    st.markdown("---")
    st.info("Tekan tombol di atas untuk mengunduh gambar resolusi tinggi Anda.")
