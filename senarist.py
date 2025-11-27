import streamlit as st
import google.generativeai as genai
import re
import datetime

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Anıl'ın Senaryo Masası", page_icon="📝", layout="wide")

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
    .quick-actions {
        display: flex;
        gap: 10px;
        margin-bottom: 20px;
        flex-wrap: wrap;
    }
</style>
""", unsafe_allow_html=True)

# --- API KEY ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    api_key = st.text_input("Google Gemini API Key", type="password")

# --- SESSION STATE ---
if 'script_content' not in st.session_state: st.session_state['script_content'] = ""
if 'history' not in st.session_state: st.session_state['history'] = []
if 'history_index' not in st.session_state: st.session_state['history_index'] = -1

def save_to_history(content, label="Düzenleme"):
    timestamp = datetime.datetime.now().strftime("%H:%M")
    st.session_state['history'].append({"time": timestamp, "label": label, "content": content})
    st.session_state['history_index'] = len(st.session_state['history']) - 1

def get_model():
    # Doğrudan en güçlü modeli döndür
    return "gemini-1.5-pro"

# --- DIALOGS ---
@st.dialog("Geçmiş Versiyon")
def show_history_item(item):
    st.write(f"**Zaman:** {item['time']}")
    st.write(f"**Etiket:** {item['label']}")
    st.text_area("İçerik", value=item['content'], height=400, disabled=True)
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        if st.button("Bu Versiyona Dön"):
            st.session_state['script_content'] = item['content']
            st.rerun()
    with col_d2:
        if st.button("Kapat"):
            st.rerun()

# --- MAIN LAYOUT ---
st.title("🎬 Senaryo Masası")

col_editor, col_ai = st.columns([2, 1])

with col_editor:
    st.markdown('<div class="white-card">', unsafe_allow_html=True)
    st.subheader("📝 Senaryo")
    
    # Hızlı İşlemler
    quick_actions = ["Daha Komik Yap", "Daha Dramatik Yap", "Diyalogları Kısalt", "Betimlemeleri Artır", "Türkçe Düzelt"]
    selected_action = st.selectbox("Hızlı İşlem Seç:", ["Seçiniz..."] + quick_actions)
    
    if selected_action != "Seçiniz...":
        if st.button("Uygula"):
            if not api_key: st.error("API Key giriniz.")
            else:
                genai.configure(api_key=api_key)
                model_name = get_model()
                with st.status(f"{selected_action} uygulanıyor...", expanded=True) as status:
                    model = genai.GenerativeModel(model_name)
                    live_text = st.session_state.get('main_editor', st.session_state['script_content'])
                    
                    action_prompt = f"""
                    GÖREV: Mevcut senaryoyu YENİDEN YAZ.
                    KULLANICI İSTEĞİ: {selected_action}
                    MEVCUT METİN:
                    {live_text}
                    
                    KESİN KURALLAR:
                    1. Metni KÖKTEN DEĞİŞTİRME hakkına sahipsin.
                    2. İsteği yerine getirmek için metni sil, ekle veya yeniden yaz.
                    3. Yazarın üslubunu koru.
                    4. DİL BİLGİSİ: Türkçe imla ve noktalama kurallarına %100 uy.
                    5. SADECE YENİ METNİ YAZ.
                    """
                    
                    # Streaming implementation for Quick Actions
                    stream_placeholder = st.empty()
                    full_response = ""
                    
                    try:
                        response = model.generate_content(action_prompt, stream=True)
                        for chunk in response:
                            if chunk.text:
                                full_response += chunk.text
                                stream_placeholder.markdown(f"**Yazılıyor...**\n\n{full_response}")
                        
                        stream_placeholder.empty()
                        st.session_state['script_content'] = full_response
                        st.session_state['editor_key'] = st.session_state.get('editor_key', 0) + 1
                        save_to_history(full_response, f"Hızlı: {selected_action}")
                        status.update(label="✅ Tamamlandı!", state="complete", expanded=False)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Hata oluştu: {e}")

    # Use unique key to force widget refresh when content changes programmatically
    if 'editor_key' not in st.session_state: st.session_state['editor_key'] = 0
    
    current_val = st.text_area(
        "Metin:", 
        value=st.session_state['script_content'], 
        height=700, 
        key=f"main_editor_{st.session_state['editor_key']}", 
        label_visibility="collapsed"
    )
    
    # Update session state with manual edits
    if current_val != st.session_state['script_content']:
        st.session_state['script_content'] = current_val
    
    # --- NAVIGATION BUTTONS ---
    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
    
    with col_nav1:
        if st.button("⬅️ Geri", use_container_width=True, disabled=(st.session_state['history_index'] <= 0)):
            if st.session_state['history_index'] > 0:
                st.session_state['history_index'] -= 1
                content = st.session_state['history'][st.session_state['history_index']]['content']
                st.session_state['script_content'] = content
                st.session_state['editor_key'] = st.session_state.get('editor_key', 0) + 1  # Force widget refresh
                st.rerun()
                
    with col_nav2:
        if st.button("⏮️ İlk Hale Dön", use_container_width=True, disabled=(not st.session_state['history'])):
            if st.session_state['history']:
                st.session_state['history_index'] = 0
                content = st.session_state['history'][0]['content']
                st.session_state['script_content'] = content
                st.session_state['editor_key'] = st.session_state.get('editor_key', 0) + 1  # Force widget refresh
                st.rerun()

    with col_nav3:
        if st.button("İleri ➡️", use_container_width=True, disabled=(st.session_state['history_index'] >= len(st.session_state['history']) - 1)):
            if st.session_state['history_index'] < len(st.session_state['history']) - 1:
                st.session_state['history_index'] += 1
                content = st.session_state['history'][st.session_state['history_index']]['content']
                st.session_state['script_content'] = content
                st.session_state['editor_key'] = st.session_state.get('editor_key', 0) + 1  # Force widget refresh
                st.rerun()

    st.download_button("💾 Kaydet (.txt)", current_val, file_name="Senaryo.txt")
    st.markdown('</div>', unsafe_allow_html=True)

with col_ai:
    st.markdown('<div class="white-card">', unsafe_allow_html=True)
    st.subheader("🤖 AI Revize")
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
            # Prompt updated to avoid prefixes
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
        st.button("🪄 AI Touch", on_click=refine_revision_prompt, help="Komutunu profesyonelleştir")
    with c_ai_2:
        if st.session_state.revize_input:
            st.button("❌ Vazgeç", on_click=clear_revision_prompt)
    
    if st.button("✨ Revize Et", type="primary"):
        if not api_key: st.error("API yok.")
        else:
            genai.configure(api_key=api_key)
            model_name = get_model()
            with st.status("✨ Revize ediliyor...", expanded=True) as status:
                # Increase temperature for creativity/change
                model = genai.GenerativeModel(model_name, generation_config=genai.types.GenerationConfig(temperature=0.8))
                # Editördeki anlık metni al - session state'den güncel hali alalım
                live_text = st.session_state.get('main_editor', st.session_state['script_content'])
                
                revize_prompt = f"""
                GÖREV: Mevcut senaryoyu YENİDEN YAZ.
                KULLANICI İSTEĞİ: {st.session_state.revize_input}
                MEVCUT METİN:
                {live_text}
                
                KESİN KURALLAR:
                1. Metni KÖKTEN DEĞİŞTİRME hakkına sahipsin.
                2. Kullanıcı isteğini YERİNE GETİRMEK İÇİN metni sil, ekle veya yeniden yaz.
                3. Asla "Yapamam" deme, sadece yap.
                4. Yazarın üslubunu koru ama içeriği isteğe göre şekillendir.
                5. DİL BİLGİSİ: Türkçe imla ve noktalama kurallarına %100 uy. Anlatım bozukluğu yapma. Akıcı ve mantıklı cümleler kur.
                6. SADECE YENİ METNİ YAZ. Başka açıklama ekleme.
                """
                
                # Streaming implementation for AI Revize
                stream_placeholder = st.empty()
                full_response = ""
                
                try:
                    response = model.generate_content(revize_prompt, stream=True)
                    for chunk in response:
                        if chunk.text:
                            full_response += chunk.text
                            stream_placeholder.markdown(f"**Yazılıyor...**\n\n{full_response}")
                    
                    stream_placeholder.empty() # Temizle
                    st.session_state['script_content'] = full_response
                    st.session_state['editor_key'] = st.session_state.get('editor_key', 0) + 1
                    save_to_history(full_response, f"Revize: {st.session_state.revize_input[:20]}...")
                    status.update(label="✅ Revize Tamamlandı!", state="complete", expanded=False)
                    st.rerun()
                except Exception as e:
                    st.error(f"Hata oluştu: {e}")
    
    st.markdown("---")
    if st.button("🗑️ Sıfırla"):
        st.session_state['script_content'] = ""
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
