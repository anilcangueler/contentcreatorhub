import streamlit as st
import google.generativeai as genai
import re

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Contentivity", page_icon=None, layout="wide")

# --- CLEAN DESIGN ---
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    h1 { color: #1a1a1a; font-family: 'Helvetica Neue', sans-serif; text-align: center; font-weight: 700; }
    h2, h3 { color: #333; font-family: 'Helvetica Neue', sans-serif; }
    .white-card { 
        background-color: white; 
        padding: 30px; 
        border-radius: 20px; 
        box-shadow: 0 10px 30px rgba(0,0,0,0.05); 
        margin-bottom: 25px; 
        border: 1px solid #eee;
    }
    .stTextArea textarea {
        background-color: #ffffff !important; 
        color: #1a1a1a !important;
        border: 2px solid #eee !important; 
        border-radius: 12px !important;
        font-size: 16px; 
        font-family: 'Arial', sans-serif; 
        line-height: 1.7;
        padding: 15px;
        transition: border-color 0.3s;
    }
    .stTextArea textarea:focus { border-color: #FF4B4B !important; }
    .stButton button { 
        background-color: #1a1a1a; 
        color: white; 
        border-radius: 10px; 
        padding: 12px 24px; 
        font-weight: 600; 
        border: none; 
        width: 100%; 
        transition: all 0.2s ease;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stButton button:hover { 
        background-color: #333; 
        transform: translateY(-2px); 
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
    /* Quick Actions Toolbar */
    div[data-testid="stHorizontalBlock"] button {
        background-color: #f0f2f6;
        color: #333;
        font-size: 14px;
        padding: 8px 12px;
    }
    div[data-testid="stHorizontalBlock"] button:hover {
        background-color: #e0e2e6;
        color: #000;
    }
</style>
""", unsafe_allow_html=True)

# --- HAFIZA ---
if 'script_content' not in st.session_state: st.session_state['script_content'] = ""
if 'style_ref' not in st.session_state: st.session_state['style_ref'] = ""
if 'history' not in st.session_state: st.session_state['history'] = []
if 'show_history' not in st.session_state: st.session_state['show_history'] = False
if 'history_index' not in st.session_state: st.session_state['history_index'] = -1

# Duration State
if 'duration_seconds' not in st.session_state: st.session_state['duration_seconds'] = 300 # 5 mins default
def format_duration(s): return f"{s//60}.{s%60:02d}"
if 'duration_input' not in st.session_state: st.session_state['duration_input'] = format_duration(st.session_state['duration_seconds'])

def update_time(delta):
    st.session_state['duration_seconds'] = max(30, st.session_state['duration_seconds'] + delta)
    st.session_state['duration_input'] = format_duration(st.session_state['duration_seconds'])

def parse_manual_time():
    try:
        val = st.session_state['duration_input'].replace(',', '.')
        if "." in val:
            parts = val.split(".")
            m = int(parts[0])
            s = int(parts[1]) if len(parts) > 1 else 0
            st.session_state['duration_seconds'] = m * 60 + s
        else:
            st.session_state['duration_seconds'] = int(val) * 60
        st.session_state['duration_input'] = format_duration(st.session_state['duration_seconds'])
    except: pass

# --- OTOMATİK API KEY OKUMA ---
api_key = None
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("API Anahtarı (secrets.toml bulunamadı)", type="password")

# --- FONKSİYONLAR ---
def clean_sbv(content):
    lines = content.splitlines()
    cleaned = [line.strip() for line in lines if not re.match(r'\d+:\d+:\d+\.\d+,\d+:\d+:\d+\.\d+', line) and line.strip()]
    return " ".join(cleaned)

def save_to_history(content, label="Versiyon"):
    import datetime
    timestamp = datetime.datetime.now().strftime("%H:%M")
    st.session_state['history'].append({"time": timestamp, "label": label, "content": content})
    st.session_state['history_index'] = len(st.session_state['history']) - 1

def get_model():
    # Gemini 2.0 Flash Experimental - Best for creative writing with unlimited RPD
    return "gemini-2.0-flash-exp"

# --- SAFETY SETTINGS ---
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

# --- DIALOGS ---
@st.dialog("Geçmiş Versiyon")
def show_history_item(item):
    st.write(f"**Zaman:** {item['time']}")
    st.write(f"**Etiket:** {item['label']}")
    st.text_area("İçerik", value=item['content'], height=400, disabled=True)
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        if st.button("Kapat", key="close_dialog"):
            st.rerun()
            
    with col_d2:
        if st.button("Bu Versiyona Geri Dön", type="primary", key="restore_dialog"):
            st.session_state['script_content'] = item['content']
            st.session_state['editor_key'] = st.session_state.get('editor_key', 0) + 1
            save_to_history(item['content'], f"Geri Yüklendi: {item['label']}")
            st.rerun()

# --- YAN MENÜ ---
with st.sidebar:
    st.header("Ayarlar")
    if api_key:
        st.success("API Anahtarı Tanımlı")
    else:
        st.warning("API Anahtarı Girilmedi")
        
    st.markdown("---")
    
    # Character Type Selector
    st.subheader("Karakter Tipi")
    character_types = [
        "Ciddi", "Samimi", "Komik", "Akıcı", "Enerjik", 
        "Sakin", "Mutsuz", "Direkt", "Dolaylı", "Profesyonel",
        "Rahat", "Heyecanlı", "Motive Edici", "Duygusal", "Eğitici",
        "Eğlenceli", "Dramatik", "İlham Verici", "Sorgulayıcı", "Hikaye Anlatıcı"
    ]
    selected_character = st.selectbox("Senaryo üslubu nasıl olsun?", character_types, key="character_type")
    
    st.markdown("---")
    st.subheader("Tarz Dosyası (Opsiyonel)")
    st.caption("Kendi üslubunuzu yüklemek için SBV, SRT veya TXT dosyası ekleyin.")
    uploaded_files = st.file_uploader("Eski Videoların", type=['sbv', 'srt', 'txt'], accept_multiple_files=True, label_visibility="collapsed")
    if uploaded_files:
        ref_text = ""
        for f in uploaded_files:
            try: 
                content = f.read().decode("utf-8")
                if f.name.endswith('.sbv') or f.name.endswith('.srt'):
                    ref_text += clean_sbv(content) + "\n\n"
                else:
                    ref_text += content + "\n\n"
            except: pass
        st.session_state['style_ref'] = ref_text
        st.success(f"{len(uploaded_files)} Dosya Yüklendi")
    else:
        st.session_state['style_ref'] = ""

# --- ANA EKRAN ---
st.title("Contentivity")

# 1. GİRİŞ EKRANI
if not st.session_state['script_content']:
    if 'topic_input' not in st.session_state: st.session_state['topic_input'] = ""
    if 'details_input' not in st.session_state: st.session_state['details_input'] = ""
    
    def generate_topic_idea():
        if not api_key:
            st.error("API Anahtarı yok!")
            return
        
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(get_model())
            category = st.session_state.get('selected_category', 'Genel')
            
            prompt = f"YouTube için '{category}' kategorisinde, her zaman izlenebilecek (evergreen), genel kitleye hitap eden, merak uyandırıcı tek bir video konusu öner. Çok spesifik veya niş olmasın. Sadece başlığı yaz."
            
            with st.spinner('Konu önerisi alınıyor...'):
                res = model.generate_content(prompt)
                st.session_state.topic_input = res.text.strip().replace('"', '')
            
            st.success("Konu önerildi!")
            st.rerun()
            
        except Exception as e:
            st.error(f"Hata oluştu: {str(e)}")

    def generate_details_idea():
        if not api_key:
            st.error("API Anahtarı yok!")
            return
        
        if not st.session_state.topic_input:
            st.warning("Önce bir konu belirle.")
            return
        
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(get_model())
            prompt = f"'{st.session_state.topic_input}' konusu için YouTube videosu içeriği oluştur. İlgi çekici 3-4 ana madde (bullet point) yaz. Kısa ve öz olsun. SADECE MADDELERİ YAZ, başka açıklama EKLEME."
            
            with st.spinner('Detaylar oluşturuluyor...'):
                res = model.generate_content(prompt)
                st.session_state.details_input = res.text.strip()
            
            st.success("Detaylar eklendi!")
            st.rerun()
            
        except Exception as e:
            st.error(f"Hata oluştu: {str(e)}")

    input_container = st.container()
    with input_container:
        st.markdown('<div class="white-card">', unsafe_allow_html=True)
        
        categories = [
            "Teknoloji & Yazılım", "Vlog & Yaşam", "Eğitim & Kişisel Gelişim", 
            "Oyun & Gaming", "Eğlence & Komedi", "Finans & Ekonomi", "Seyahat & Gezi",
            "Sağlık & Fitness", "Yemek & Tarifler", "Bilim & Teknoloji", 
            "Tarih & Belgesel", "Motivasyon & Psikoloji", "Sanat & Tasarım"
        ]
        selected_category = st.selectbox("Kategori Seç", categories, key="selected_category")
        st.markdown("---")

        col1, col2 = st.columns([2, 1])
        with col1:
            c_t1, c_t2 = st.columns([8, 1])
            with c_t1:
                st.text_input("Konu", placeholder="Örn: Ev Stüdyosu", key="topic_input")
            with c_t2:
                st.button("Rastgele", on_click=generate_topic_idea, help="Rastgele Fikir Ver")
                
            c_d1, c_d2 = st.columns([8, 1])
            with c_d1:
                st.text_area("Detaylar", placeholder="Değinilecek maddeler...", height=150, key="details_input")
            with c_d2:
                st.button("Öner", on_click=generate_details_idea, help="İçerik Öner")

        with col2:
            st.markdown("<label style='font-size:14px;'>Süre (Dk.Sn)</label>", unsafe_allow_html=True)
            cd1, cd2, cd3 = st.columns([1, 2, 1])
            cd1.button("-", on_click=update_time, args=(-30,), use_container_width=True)
            cd2.text_input("Süre", key="duration_input", on_change=parse_manual_time, label_visibility="collapsed")
            cd3.button("+", on_click=update_time, args=(30,), use_container_width=True)
            
            st.markdown("<br><br>", unsafe_allow_html=True)
            create_btn = st.button("Senaryoyu Yaz")
        st.markdown('</div>', unsafe_allow_html=True)

    if create_btn:
        if not api_key: 
            st.error("API Anahtarı yok! secrets.toml dosyasını kontrol et.")
        else:
            if st.session_state.get('style_ref'):
                prompt = f"""
                GÖREV: YouTube Video Senaryo Yazarı (Stil Transferi).
                
                KESİN KURALLAR:
                1. Referans metindeki HİKAYELERİ, ANILARI, ÖZEL İSİMLERİ TAMAMEN GÖRMEZDEN GEL - Sadece "Ses Tonu" ve "Konuşma Tarzı"nı kopyala.
                2. SADECE OKUMA METNİNİ YAZ - "Harika bir konu!", "İşte taslak" gibi AÇIKLAMALAR EKLEME.
                3. Direkt senaryo metnini ver - İntro, açıklama, başlık yazma.
                4. Türkçe dil kurallarına %100 uy - İmla, noktalama kusursuz olsun.
                5. GERÇEKLİK KONTROLÜ: Eğer konu gerçek bir ürün/kişi/olay ise, BİLDİĞİN GERÇEK BİLGİLERİ kullan. Asla uydurma isim veya özellik yazma.

                REFERANS METİN (Sadece Üslup İçin):
                {st.session_state['style_ref'][:30000]}

                YENİ KONU: {st.session_state.topic_input}
                DETAYLAR: {st.session_state.details_input}
                HEDEF SÜRE: {st.session_state['duration_input']} dakika
                
                OUTPUT: Sadece okuma metnini ver. Başka hiçbir şey yazma.
                """
            else:
                character = st.session_state.get('character_type', 'Samimi')
                prompt = f"""
                GÖREV: YouTube Video Senaryo Yazarı.
                
                KESİN KURALLAR:
                1. SADECE OKUMA METNİNİ YAZ - "Harika bir konu!", "İşte taslak" gibi AÇIKLAMALAR EKLEME.
                2. Direkt senaryo metnini ver - İntro, açıklama, başlık yazma.
                3. Türkçe dil kurallarına %100 uy - İmla, noktalama kusursuz olsun.
                4. Karakter: {character} - Bu tonu kullan.
                5. GERÇEKLİK KONTROLÜ: Eğer konu gerçek bir ürün/kişi/olay ise, BİLDİĞİN GERÇEK BİLGİLERİ kullan. Asla uydurma isim veya özellik yazma.

                KONU: {st.session_state.topic_input}
                DETAYLAR: {st.session_state.details_input}
                HEDEF SÜRE: {st.session_state['duration_input']} dakika
                
                OUTPUT: Sadece okuma metnini ver.
                """
            
            # Set task and switch view
            st.session_state['generation_task'] = prompt
            st.session_state['generation_temp'] = 0.8 # Creative for initial
            st.session_state['script_content'] = " " # Placeholder to switch to editor view
            st.rerun()

# 2. DÜZENLEME EKRANI
else:
    col_editor, col_ai = st.columns([2, 1])
    
    with col_editor:
        st.markdown('<div class="white-card">', unsafe_allow_html=True)
        
        if st.session_state['history']:
            st.subheader("Geçmiş Versiyonlar")
            h_cols = st.columns(min(5, len(st.session_state['history'])))
            for idx, item in enumerate(st.session_state['history'][-5:]):
                with h_cols[idx % 5]:
                    if st.button(f"{item['time']}\n{item['label'][:15]}...", key=f"history_{idx}", use_container_width=True):
                        show_history_item(item)
            st.markdown("---")
        
        st.subheader("Hızlı İşlemler")
        quick_actions = [
            ("Daha Komik", ""), ("Daha Kısa", ""), ("Daha Uzun", ""), 
            ("Dramatik", ""), ("Türkçe Düzelt", "")
        ]
        
        quick_cols = st.columns(len(quick_actions))
        for idx, (action, emoji) in enumerate(quick_actions):
            with quick_cols[idx]:
                if st.button(f"{action}", key=f"quick_{action}", use_container_width=True):
                    if not api_key: st.error("API yok.")
                    else:
                        live_text = st.session_state.get('main_editor', st.session_state['script_content'])
                        
                        revize_prompt = f"""
                        GÖREV: Mevcut senaryoyu KULLANICI İSTEĞİNE göre DÜZENLE (Revize Et).
                        
                        KULLANICI İSTEĞİ: {action}
                        
                        MEVCUT METİN:
                        {live_text}
                        
                        KESİN KURALLAR:
                        1. KONUYU, ANA FİKRİ VE ÖRNEKLERİ ASLA DEĞİŞTİRME.
                        2. Sadece kullanıcının istediği değişikliği uygula.
                        3. Metnin içindeki özel isimleri, sayıları ve verileri KORU.
                        4. METNİ KOMPLE BAŞTAN YAZMA. Sadece gerekli cümleleri düzenle.
                        5. GERÇEKLİK KONTROLÜ: Kullanıcının verdiği ürün/kişi isimlerini AYNEN KULLAN. Asla "sansürlemek" için uydurma isimler (örn: Yaşlı Kurt) kullanma.
                        6. DİL BİLGİSİ: Türkçe imla ve noktalama kurallarına %100 uy.
                        7. ÇIKTI: Sadece revize edilmiş tam metni ver.
                        """
                        
                        st.session_state['generation_task'] = revize_prompt
                        st.session_state['generation_temp'] = 0.3 # Focused for revision
                        st.rerun()

        if 'editor_key' not in st.session_state: st.session_state['editor_key'] = 0
        
        if 'editor_key' not in st.session_state: st.session_state['editor_key'] = 0
        
        # Check for pending generation task (Unified Handler)
        if 'generation_task' in st.session_state:
            # Create streaming placeholder in main editor area
            stream_container = st.empty()
            full_response = ""
            
            try:
                stream_container.markdown("**AI Yazıyor...**")
                
                genai.configure(api_key=api_key)
                model_name = get_model()
                temp = st.session_state.get('generation_temp', 0.7)
                model = genai.GenerativeModel(model_name, generation_config=genai.types.GenerationConfig(temperature=temp), safety_settings=safety_settings)
                
                response = model.generate_content(st.session_state['generation_task'], stream=True)
                for chunk in response:
                    if chunk.text:
                        full_response += chunk.text
                        # Update placeholder with streaming content
                        stream_container.markdown(f"**AI Yazıyor...**\n\n{full_response}")
                
                # Clear placeholder and update session state
                stream_container.empty()
                st.session_state['script_content'] = full_response
                st.session_state['editor_key'] = st.session_state.get('editor_key', 0) + 1
                
                # Determine label based on context (simple heuristic)
                task_text = st.session_state['generation_task']
                if "Stil Transferi" in task_text or "YouTube Video Senaryo Yazarı" in task_text:
                    label = "İlk Taslak"
                elif "KULLANICI İSTEĞİ" in task_text:
                    # Extract request from prompt if possible, or just generic
                    label = "Revize"
                else:
                    label = "AI Versiyon"
                    
                save_to_history(full_response, label)
                
                # Clear task
                del st.session_state['generation_task']
                if 'generation_temp' in st.session_state: del st.session_state['generation_temp']
                st.rerun()
                
            except Exception as e:
                stream_container.empty()
                st.error(f"Hata: {e}")
                if 'generation_task' in st.session_state: del st.session_state['generation_task']
                if 'generation_temp' in st.session_state: del st.session_state['generation_temp']

        else:
            current_val = st.text_area(
                "Metin:", 
                value=st.session_state['script_content'], 
                height=700, 
                key=f"main_editor_{st.session_state['editor_key']}", 
                label_visibility="collapsed"
            )
        
        if current_val != st.session_state['script_content']:
            st.session_state['script_content'] = current_val
        
        col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
        
        with col_nav1:
            if st.button("Geri", use_container_width=True, disabled=(st.session_state['history_index'] <= 0)):
                if st.session_state['history_index'] > 0:
                    st.session_state['history_index'] -= 1
                    content = st.session_state['history'][st.session_state['history_index']]['content']
                    st.session_state['script_content'] = content
                    st.session_state['editor_key'] = st.session_state.get('editor_key', 0) + 1
                    st.rerun()
                    
        with col_nav2:
            if st.button("İlk Hale Dön", use_container_width=True, disabled=(not st.session_state['history'])):
                if st.session_state['history']:
                    st.session_state['history_index'] = 0
                    content = st.session_state['history'][0]['content']
                    st.session_state['script_content'] = content
                    st.session_state['editor_key'] = st.session_state.get('editor_key', 0) + 1
                    st.rerun()

        with col_nav3:
            if st.button("İleri", use_container_width=True, disabled=(st.session_state['history_index'] >= len(st.session_state['history']) - 1)):
                if st.session_state['history_index'] < len(st.session_state['history']) - 1:
                    st.session_state['history_index'] += 1
                    content = st.session_state['history'][st.session_state['history_index']]['content']
                    st.session_state['script_content'] = content
                    st.session_state['editor_key'] = st.session_state.get('editor_key', 0) + 1
                    st.rerun()

        st.download_button("Kaydet (.txt)", current_val, file_name="Senaryo.txt")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_ai:
        st.markdown('<div class="white-card">', unsafe_allow_html=True)
        st.subheader("AI Revize")
        if 'revize_input' not in st.session_state: st.session_state['revize_input'] = ""
        
        def refine_revision_prompt():
            if not api_key: 
                st.error("API yok.")
                return
            if not st.session_state.revize_input: 
                st.warning("Bir şeyler yaz.")
                return
            
            genai.configure(api_key=api_key)
            model_name = get_model()
            try:
                model = genai.GenerativeModel(model_name)
                refine_prompt = f"""
                GÖREV: Aşağıdaki senaryo revize komutunu, bir yapay zeka modelinin daha iyi anlayacağı şekilde netleştir, detaylandır ve profesyonelleştir.
                
                ORİJİNAL KOMUT: {st.session_state.revize_input}
                
                Sadece yeni komutu yaz. "YENİ KOMUT:" gibi başlıklar EKLEME. Direkt metni ver.
                """
                res = model.generate_content(refine_prompt)
                st.session_state.revize_input = res.text.strip()
            except Exception as e:
                st.error(f"Hata: {e}")

        def clear_revision_prompt():
            st.session_state.revize_input = ""

        st.text_area("İsteklerin:", placeholder="Örn: Girişi kısalt...", height=150, key="revize_input")
        
        c_ai_1, c_ai_2 = st.columns([1, 1])
        with c_ai_1:
            st.button("AI Touch", on_click=refine_revision_prompt, help="Komutunu profesyonelleştir")
        with c_ai_2:
            if st.session_state.revize_input:
                st.button("Vazgeç", on_click=clear_revision_prompt)
        
        if st.button("Revize Et", type="primary"):
            if not api_key: st.error("API yok.")
            else:
                live_text = st.session_state.get('main_editor', st.session_state['script_content'])
                
                revize_prompt = f"""
            GÖREV: Mevcut senaryoyu KULLANICI İSTEĞİNE göre DÜZENLE (Revize Et).
            
            KULLANICI İSTEĞİ: {st.session_state.revize_input}
            
            MEVCUT METİN:
            {live_text}
            
            KESİN KURALLAR:
            1. KONUYU, ANA FİKRİ VE ÖRNEKLERİ ASLA DEĞİŞTİRME.
            2. Sadece kullanıcının istediği değişikliği uygula.
            3. Metnin içindeki özel isimleri, sayıları ve verileri KORU.
            4. METNİ KOMPLE BAŞTAN YAZMA. Sadece gerekli cümleleri düzenle.
            5. GERÇEKLİK KONTROLÜ: Kullanıcının verdiği ürün/kişi isimlerini AYNEN KULLAN. Asla "sansürlemek" için uydurma isimler (örn: Yaşlı Kurt) kullanma.
            6. ARAŞTIRMA: Eğer bahsedilen konu gerçek bir ürünse, teknik detayları doğru kullan.
            7. DİL BİLGİSİ: Türkçe imla ve noktalama kurallarına %100 uy.
            8. ÇIKTI: Sadece revize edilmiş tam metni ver.
            """
                
                # Set task and rerun to trigger processing in main editor column
                st.session_state['generation_task'] = revize_prompt
                st.session_state['generation_temp'] = 0.3 # Focused for revision
                st.rerun()
        
        st.markdown("---")
        if st.button("Sıfırla"):
            st.session_state['script_content'] = ""
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

