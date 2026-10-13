import streamlit as st
import pandas as pd
import joblib
import numpy as np
import time
from datetime import datetime # Rapor tarihi için eklendi

# 1. Arayüz ayarları
st.set_page_config(page_title="EHMS - Engine Health Monitoring System", layout="wide")
st.title("✈️ Entegre Uçak Motoru Sağlık Takip Sistemi (EHMS)")
st.markdown("---")

# 2. Modelleri yükleme
@st.cache_resource
def modelleri_yukle():
    try:
        model = joblib.load('xgboost_rul_modeli.joblib')
        scaler = joblib.load('veri_olceklendirici.joblib')
        ozellik_sutunlari = joblib.load('ozellik_sutunlari.joblib')
        return model, scaler, ozellik_sutunlari
    except Exception as e:
        st.error(f"Sistem başlatılamadı: {e}")
        return None, None, None

model, scaler, ozellik_sutunlari = modelleri_yukle()

# 3. Alt Sistem Haritalaması ve Fonksiyonlar
ALT_SISTEMLER = {
    'Yüksek Basınç Kompresörü (HPC)': ['Sensor_3', 'Sensor_7', 'Sensor_11', 'Sensor_17'],
    'Türbin Modülü (HPT/LPT)': ['Sensor_4', 'Sensor_20', 'Sensor_21'],
    'Fan ve Bypass Kanalı': ['Sensor_2', 'Sensor_8', 'Sensor_13', 'Sensor_15'],
    'Çekirdek Motor / Yanma Odası': ['Sensor_9', 'Sensor_12', 'Sensor_14']
}

def ariza_kaynagi_bul(olcekli_veri_satiri, ozellik_isimleri):
    degerler = dict(zip(ozellik_isimleri, olcekli_veri_satiri))
    en_riskli_sistem = "Bilinmiyor"
    maks_sapma = -1
    for sistem, sensorler in ALT_SISTEMLER.items():
        sistem_sapmalari = [degerler[s] for s in sensorler if s in degerler]
        if sistem_sapmalari:
            ortalama_sapma = np.mean(sistem_sapmalari)
            if ortalama_sapma > maks_sapma:
                maks_sapma = ortalama_sapma
                en_riskli_sistem = sistem
    return en_riskli_sistem

def ucus_zorlugu_hesapla(op_1, op_2, op_3):
    stres_katsayisi = abs(op_1) + abs(op_2) + (100 - abs(op_3))
    if stres_katsayisi > 20: return "Yüksek (Agresif Uçuş)"
    elif stres_katsayisi > 5: return "Orta (Dalgalı Uçuş)"
    else: return "Standart (Deniz Seviyesi)"

def durum_renklendir(val):
    if val < 50: return 'background-color: #ffcccc; color: #990000; font-weight: bold;'
    elif val < 100: return 'background-color: #fff3cc; color: #996600;'
    else: return 'background-color: #d4edda; color: #155724;'

# YENİ: Otonom İş Emri (Work Order) Oluşturucu
def is_emri_olustur(motor_id, ucus_sayisi, rul, kaynak, zorluk):
    zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rapor = f"""
    ===============================================================
    TUSAŞ/TÜBİTAK - ENTEGRE UÇAK MOTORU SAĞLIK TAKİP SİSTEMİ (EHMS)
    ===============================================================
    BELGE TÜRÜ: ACİL BAKIM İŞ EMRİ (WORK ORDER)
    TARİH/SAAT: {zaman}
    
    [MOTOR BİLGİLERİ]
    Motor ID: {motor_id}
    Tamamlanan Toplam Uçuş Döngüsü: {ucus_sayisi}
    Uçuş Görev Profili (Stres): {zorluk}
    
    [YAPAY ZEKA TEŞHİSİ]
    Kalan Faydalı Ömür (RUL): {rul} Uçuş (KRİTİK SEVİYE)
    İzole Edilen Arıza Kaynağı: {kaynak}
    
    [OTONOM SİSTEM TAVSİYESİ VE AKSİYON]
    Motorun tahmini ömrü 50 uçuşun altına düşmüştür. Yapay zeka 
    algoritmaları arıza kök nedeni olarak '{kaynak}' 
    modülünü işaret etmektedir. Motorun acilen uçuştan çekilerek ilgili 
    bölgesinin boreskop (kamera) denetiminden geçirilmesi zorunludur.
    ===============================================================
    EHMS Otonom Karar Destek Sistemi
    """
    return rapor

# 4. Sol Panel ve Veri Yükleme
st.sidebar.header("📡 Telemetri Veri Girişi")
yuklenen_dosya = st.sidebar.file_uploader("Motor Sensör Verisi Yükle", type=["txt", "csv"])

if yuklenen_dosya is not None:
    df_test = pd.read_csv(yuklenen_dosya, sep=r"\s+", header=None)
    sutunlar = ['Motor_ID', 'Zaman_Dongusu', 'Op_Ayar_1', 'Op_Ayar_2', 'Op_Ayar_3'] + [f'Sensor_{i}' for i in range(1, 22)]
    df_test.columns = sutunlar
    
    st.sidebar.markdown("---")
    st.sidebar.header("🔴 Canlı İzleme Merkezi")
    secilen_motor = st.sidebar.selectbox("İzlenecek Motoru Seçin", df_test['Motor_ID'].unique())
    canli_yayin = st.sidebar.button("🚀 Canlı Telemetriyi Başlat")
    
    if canli_yayin:
        st.subheader(f"📡 Motor {secilen_motor} - Canlı Uçuş Telemetrisi")
        
        motor_verisi = df_test[df_test['Motor_ID'] == secilen_motor].copy()
        
        tablo_alani = st.empty()
        uyari_alani = st.empty() # Acil uyarı butonu için boş alan
        gecmis_veriler = pd.DataFrame()
        
        kritik_seviye_goruldu = False
        son_durum = {}
        
        for index, row in motor_verisi.iterrows():
            X_anlik = row[ozellik_sutunlari].values.reshape(1, -1)
            X_anlik_olcekli = scaler.transform(pd.DataFrame(X_anlik, columns=ozellik_sutunlari))
            
            anlik_rul = int(model.predict(X_anlik_olcekli)[0])
            kaynak = "Normal" if anlik_rul > 100 else ariza_kaynagi_bul(X_anlik_olcekli[0], ozellik_sutunlari)
            zorluk = ucus_zorlugu_hesapla(row['Op_Ayar_1'], row['Op_Ayar_2'], row['Op_Ayar_3'])
            
            yeni_satir = {
                'Zaman Döngüsü (Uçuş)': int(row['Zaman_Dongusu']),
                'Anlık Kalan Ömür (RUL)': anlik_rul,
                'Olası Arıza Kaynağı': kaynak,
                'Uçuş Görev Profili': zorluk
            }
            
            gecmis_veriler = pd.concat([gecmis_veriler, pd.DataFrame([yeni_satir])], ignore_index=True)
            
            gosterilecek = gecmis_veriler.tail(8).copy()
            renkli_tablo = gosterilecek.style.map(durum_renklendir, subset=['Anlık Kalan Ömür (RUL)'])
            
            with tablo_alani:
                st.dataframe(renkli_tablo, use_container_width=True, hide_index=True)
            
            # Eğer RUL 50'nin altına düşerse sistemi uyar
            if anlik_rul < 50:
                kritik_seviye_goruldu = True
                son_durum = yeni_satir
                
            time.sleep(0.2)
            
        st.success(f"Motor {secilen_motor} için telemetri veri akışı tamamlandı.")
        
        # Uçuş bittiğinde veya kesildiğinde, eğer kritik seviye görüldüyse buton çıkar
        if kritik_seviye_goruldu:
            with uyari_alani:
                rapor_metni = is_emri_olustur(secilen_motor, son_durum['Zaman Döngüsü (Uçuş)'], son_durum['Anlık Kalan Ömür (RUL)'], son_durum['Olası Arıza Kaynağı'], son_durum['Uçuş Görev Profili'])
                st.error("⚠️ KRİTİK UYARI: Uçuş sırasında motor ömrü 50'nin altına düştü! Sistem otonom bakım iş emri üretti.")
                st.download_button(
                    label="📄 Acil Bakım İş Emrini İndir (TXT)",
                    data=rapor_metni,
                    file_name=f"Acil_Bakim_Emri_Motor_{secilen_motor}.txt",
                    mime="text/plain"
                )
    else:
        st.info("👈 Sol panelden bir motor seçin ve 'Canlı Telemetriyi Başlat' butonuna basarak sistemi test edin.")
else:
    st.info("Sistemi test etmek için sol panelden bir uçuş telemetri dosyası yükleyiniz.")