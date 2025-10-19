import streamlit as st
from PIL import Image
import google.generativeai as genai
import os
from dotenv import load_dotenv
# --- GEÇİCİ TEST KODU ---
print("--- API Anahtarı Testi Başlıyor ---")
load_dotenv() # .env dosyasını yüklemeyi dene (Cloud'da başarısız olacak)
api_key_test = os.getenv("GOOGLE_API_KEY")

if api_key_test:
    print(f"API Anahtarı bulundu! İlk 5 karakter: {api_key_test[:5]}...") # Anahtarın tamamını yazdırma!
    st.success("API Anahtarı ortam değişkenlerinden başarıyla okundu.") # Ekranda da görelim
else:
    print("HATA: API Anahtarı ortam değişkenlerinde bulunamadı!")
    st.error("HATA: API Anahtarı ortam değişkenlerinde bulunamadı! Lütfen Streamlit Secrets ayarlarını kontrol edin.")
print("--- API Anahtarı Testi Bitti ---")
# --- GEÇİCİ TEST KODU BİTTİ ---
from streamlit_lottie import st_lottie
import requests

# --- YARDIMCI FONKSİYONLAR ---

def local_css(file_name):
    """Lokal CSS dosyasını uygulamaya yükler."""
    try:
        with open(file_name, encoding='utf-8') as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"'{file_name}' stil dosyası bulunamadı.")
    except Exception as e:
        st.error(f"Stil dosyası okunurken hata oluştu: {e}")

def load_lottieurl(url: str):
    """Verilen URL'den bir Lottie animasyonunu yükler."""
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

# --- UYGULAMA YAPILANDIRMASI VE BAŞLANGIÇ AYARLARI ---

# .env dosyasından ortam değişkenlerini (API anahtarı) yükle
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

# Google Generative AI istemcisini yapılandır
try:
    genai.configure(api_key=api_key)
except Exception as e:
    st.error(f"API anahtarı yapılandırılamadı. Lütfen .env dosyasını kontrol edin. Hata: {e}")

# Modelin güvenlik filtrelerini daha esnek bir seviyeye ayarla
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

# Kullanılacak yapay zeka modelini tanımla
model = genai.GenerativeModel('gemini-2.5-flash')

# --- SİSTEM TALİMATLARI (PROMPTLAR) ---

# BEYİN 1: Görselden prompt üreten ana sistem talimatı
system_prompt_generator = """
Sen, usta bir fotoğrafçı ve bir prompt mühendisisin. Sana yüklenen görseli bir sanat eseri gibi en ince detayına kadar analiz et. 
Işığı, renk paletini, kompozisyonu, objeleri, sanatsal stili ve duyguyu incele.
Bu analize dayanarak, bu görseli Midjourney gibi bir yapay zeka modelinde yeniden oluşturabilecek, son derece detaylı ve profesyonel bir prompt üret. 
Bu prompt'ta diyafram (f-stop), ISO, lens türü (örn: 85mm f/1.8) gibi teknik detayları görselin tarzına göre **tahmin ederek** ekle.
Sonuna `--ar 16:9 --v 6.0` gibi ekstra parametreler ekle.
Çıktın sadece bu prompt metni olsun, başka hiçbir açıklama yapma.
"""

# BEYİN 2: Mevcut bir prompt'u düzenleyen sistem talimatı
system_prompt_modifier = """
Sen, bir prompt mühendisi asistanısın. Görevin, sana verilen bir ana prompt'u, kullanıcının isteği doğrultusunda düzenlemektir.
Kullanıcının isteğini dikkatlice anla ve ana prompt üzerinde sadece istenen değişikliği yaparak yeni bir prompt oluştur.
Tarzı, formatı ve diğer detayları koru. Çıktın sadece güncellenmiş prompt metni olsun.
"""

# BEYİN 3: Kullanıcı niyetini anlayan sınıflandırıcı sistem talimatı
system_prompt_classifier = """
Kullanıcının yazdığı cümlenin niyetini analiz et.
Eğer cümle, var olan bir prompt'u değiştirmeye yönelik bir komut içeriyorsa (örn: 'anime yap', 'daha detaylı olsun', 'ışığı değiştir'), sadece 'modifikasyon' yaz.
Eğer cümle, teşekkür, selamlama, iltifat gibi normal bir sohbet ifadesi ise, sadece 'sohbet' yaz.
Çıktın sadece bu iki kelimeden biri olsun.
"""

# BEYİN 4: Sohbet cevapları üreten sistem talimatı
system_prompt_conversational = """
Sen, AI Prompt Mühendisi Botu'nun yardımsever ve samimi sohbet kişiliğisin.
Kullanıcının yazdığı sohbet cümlesine uygun, kısa ve pozitif bir cevap ver.
"""

# --- CALLBACK FONKSİYONU ---

def handle_update():
    """Kullanıcı 'Gönder' butonuna bastığında çalışacak ana mantık fonksiyonu."""
    modification_request = st.session_state.modification_input
    if not modification_request:
        st.warning("Lütfen bir değişiklik isteği girin.")
        return

    with st.spinner("İsteğiniz işleniyor..."):
        try:
            # 1. Niyet Tespiti: Kullanıcının girdisi bir komut mu, sohbet mi?
            classifier_response = model.generate_content(
                [system_prompt_classifier, modification_request],
                generation_config=genai.types.GenerationConfig(temperature=0.0), 
                safety_settings=safety_settings
            )
            intent = classifier_response.text.strip().lower()

            # 2. Niyete Göre Aksiyon:
            if "modifikasyon" in intent:
                # Eğer niyet prompt'u değiştirmekse, Beyin 2'yi kullan
                update_request_full = f"ANA PROMPT:\n{st.session_state.latest_prompt}\n\nKULLANICI İSTEĞİ:\n{modification_request}"
                response = model.generate_content(
                    [system_prompt_modifier, update_request_full],
                    generation_config=genai.types.GenerationConfig(temperature=0.4), 
                    safety_settings=safety_settings
                )
                modified_prompt = response.text
                st.session_state.latest_prompt = modified_prompt
                st.session_state.gallery[0]["prompt"] = modified_prompt
                st.session_state.update_success = True
                
            elif "sohbet" in intent:
                # Eğer niyet sohbet etmekse, Beyin 4'ü kullan
                response = model.generate_content(
                    [system_prompt_conversational, modification_request],
                    generation_config=genai.types.GenerationConfig(temperature=0.7), 
                    safety_settings=safety_settings
                )
                conversational_reply = response.text
                st.toast(f'{conversational_reply}', icon='🤖')
            
            else:
                # Eğer niyet anlaşılamazsa, kullanıcıyı uyar
                st.warning("İsteğinizi anlayamadım. Lütfen prompt'u değiştirmek için bir komut girin (örn: 'daha karanlık yap').")

            # İşlem sonrası input kutusunu temizle
            st.session_state.modification_input = ""

        except Exception as e:
            st.error(f"İsteğiniz işlenirken bir hata oluştu: {e}")

# --- STREAMLIT ARAYÜZÜNÜN ÇİZİLMESİ ---

# Sayfa yapılandırması ve başlık
st.set_page_config(page_title="Prompt Mühendisi", page_icon="🎨", layout="wide")
local_css(".streamlit/style.css") # Özel CSS dosyasını yükle

# Kenar Çubuğu (Sidebar)
with st.sidebar:
    st.header("🎨 AI Prompt Mühendisi")
    lottie_url = "https://lottie.host/2e71c849-5999-4625-861f-173a6a1d48b2/V7v2u10a26.json"
    lottie_animation = load_lottieurl(lottie_url)
    if lottie_animation:
        st_lottie(lottie_animation, height=150, key="ai_animation")
    
    st.markdown("---")
    st.image("assets/reklam.png") # Kenar çubuğundaki tanıtım görseli
    st.markdown("---")
    st.markdown("Bu araç, görselleri analiz ederek onları yeniden yaratabileceğiniz sihirli prompt'lar üretir.")
    st.markdown("Geliştirici: **Akif Emre Demir**")

# Ana Başlık ve Açıklamalar
st.title("🎨 AI Prompt Mühendisi Botu")
st.caption("Yüklediğin görselleri analiz ederek onları yeniden yaratabileceğin sihirli prompt'lar üreten yapay zeka asistanın.")

with st.expander("🤔 Bu Araç Nasıl Çalışıyor? (Teknik Detaylar)"):
    st.markdown("""
        Bu uygulama, RAG mimarisinin multimodal bir yorumudur. Gemini 2.5 Flash modeli, yüklenen görseli analiz eder ve bu bilgiyi kullanarak detaylı bir metin istemi (prompt) üretir.
    """)

# Oturum durumunu (session state) yönetimi için hafıza değişkenlerini başlat
if 'gallery' not in st.session_state: st.session_state.gallery = []
if 'latest_prompt' not in st.session_state: st.session_state.latest_prompt = None
if 'original_prompt' not in st.session_state: st.session_state.original_prompt = None
if 'update_success' not in st.session_state: st.session_state.update_success = False

# Arayüzü iki ana sütuna böl
col1, col2 = st.columns(2)

# Sol Sütun: Görsel Yükleme
with col1:
    with st.container(border=True):
        st.header("1. Görselini Yükle")
        st.info("🔒 Gizliliğiniz bizim için önemli! Yüklediğiniz görseller ve oluşturulan prompt'lar hiçbir yere kaydedilmez. Sayfayı yenilediğinizde veya kapattığınızda tüm veriler silinir.", icon="ℹ️")
        uploaded_file = st.file_uploader("Bir görsel seç...", type=["png", "jpg", "jpeg"], label_visibility="collapsed")

        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            st.image(image, caption='Analiz Edilecek Görsel', use_container_width=True)
            
            if st.button('✨ Sihirli Prompt Oluştur ✨', use_container_width=True):
                with st.spinner('Görsel analiz ediliyor...'):
                    # İlk prompt'u oluşturmak için Beyin 1'i kullan
                    response = model.generate_content(
                        [system_prompt_generator, image],
                        generation_config=genai.types.GenerationConfig(temperature=0.4),
                        safety_settings=safety_settings
                    )
                    generated_prompt = response.text
                    # Sonuçları hafızaya kaydet ve arayüzü yenile
                    st.session_state.original_prompt = generated_prompt
                    st.session_state.latest_prompt = generated_prompt
                    st.session_state.gallery.insert(0, {"image": image, "prompt": generated_prompt, "original": generated_prompt})
                    st.rerun()

# Sağ Sütun: Sonuç ve Sohbet Alanı
with col2:
    with st.container(border=True):
        st.header("2. Sonuç ve Düzenleme")
        
        # Prompt güncellendiğinde gösterilecek başarı mesajı
        if st.session_state.update_success:
            st.success("Prompt güncellendi! Aşağıda en güncel halini bulabilirsiniz.")
            st.session_state.update_success = False

        # Eğer bir prompt oluşturulduysa, sonuçları ve sohbet kutusunu göster
        if st.session_state.latest_prompt:
            # Güncellenmiş ve orijinal prompt'ları karşılaştırmalı olarak göster
            if st.session_state.original_prompt != st.session_state.latest_prompt:
                st.subheader("Güncellenmiş Prompt")
                st.code(st.session_state.latest_prompt, language='text')
                with st.expander("Orijinal Prompt'u Gör"):
                    st.code(st.session_state.original_prompt, language='text')
            else:
                st.subheader("Oluşturulan Prompt")
                st.code(st.session_state.latest_prompt, language='text')
            
            # Sohbet ve düzenleme için input alanı
            st.divider()
            st.subheader("💬 Bot ile Konuş")
            st.text_input("Prompt'u düzenle veya bot ile sohbet et...", key="modification_input")
            st.button("Gönder", use_container_width=True, on_click=handle_update)
        else:
            # Henüz bir işlem yapılmadıysa bilgilendirme mesajı göster
            st.info("Henüz bir prompt oluşturulmadı. Lütfen soldan bir görsel yükleyin.")

st.divider()

# Galeri Bölümü
with st.container(border=True):
    st.header("🖼️ Galeri: Önceki Çalışmalar")
    st.caption("Bu galeri sadece sizin mevcut oturumunuz için geçerlidir ve tarayıcıyı kapattığınızda silinir.")

    if not st.session_state.gallery:
        st.image("assets/reklam.png", caption="Kendi çalışmanızı oluşturmak için bir görsel yükleyin!")
    else:
        # Galeriyi 3 sütunlu bir yapıda göster
        gallery_cols = st.columns(3)
        for i, item in enumerate(st.session_state.gallery):
            with gallery_cols[i % 3]:
                st.image(item["image"], use_container_width=True, caption=f"Çalışma #{len(st.session_state.gallery) - i}")
                with st.expander("Prompt'u Gör"):
                    if item["original"] != item["prompt"]:
                         st.write("**Güncellenmiş Hali:**")
                         st.code(item["prompt"], language='text')
                         st.write("**Orijinal Hali:**")
                         st.code(item["original"], language='text')
                    else:
                         st.code(item["prompt"], language='text')
