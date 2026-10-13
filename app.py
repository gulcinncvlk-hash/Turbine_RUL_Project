import streamlit as st
import pandas as pd
import numpy as np
import time
import requests 
from datetime import datetime
import joblib

# HATALI KISIM DÜZELTİLDİ: yeni_kullanici_ekle fonksiyonu import'tan çıkarıldı.
from database import (veritabani_kur, is_emri_kaydet, tum_is_emirlerini_getir, 
                      kullanici_dogrula, log_kaydet, tum_loglari_getir)

st.set_page_config(page_title="EHMS - Kurumsal Frontend", layout="wide")
veritabani_kur()

if 'giris_yapildi' not in st.session_state:
    st.session_state.giris_yapildi = False
    st.session_state.aktif_rol = ""
    st.session_state.aktif_kullanici = ""

try:
    ozellik_sutunlari = joblib.load('ozellik_sutunlari_v2.joblib')
except:
    ozellik_sutunlari = []

def durum_renklendir(val):
    if val < 50: return 'background-color: #ffcccc; color: #990000; font-weight: bold;'
    elif val < 100: return 'background-color: #fff3cc; color: #996600;'
    else: return 'background-color: #d4edda; color: #155724;'

def is_emri_olustur(motor_id, ucus_sayisi, rul, kaynak, zorluk):
    zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""===============================================================
TUSAŞ/TÜBİTAK - EHMS OTONOM BAKIM İŞ EMRİ
===============================================================
TARİH/SAAT: {zaman}
ONAYLAYAN YETKİLİ: {st.session_state.aktif_kullanici.upper()} ({st.session_state.aktif_rol})
MOTOR ID: {motor_id}
KALAN ÖMÜR: {rul} Uçuş
ARIZA KAYNAĞI: {kaynak}
==============================================================="""

if not st.session_state.giris_yapildi:
    st.title("🔒 EHMS Kurumsal Giriş Paneli")
    st.markdown("Sisteme erişmek için yetkilendirilmiş kimlik bilgilerinizi giriniz.")
    
    with st.form("giris_formu"):
        kullanici = st.text_input("Kullanıcı Adı")
        sifre = st.text_input("Şifre", type="password")
        giris_butonu = st.form_submit_button("Sisteme Bağlan")
        
        if giris_butonu:
            basarili, rol = kullanici_dogrula(kullanici, sifre)
            if basarili:
                st.session_state.giris_yapildi = True
                st.session_state.aktif_kullanici = kullanici
                st.session_state.aktif_rol = rol
                log_kaydet(kullanici, "Sisteme başarılı giriş yaptı.")
                st.rerun() 
            else:
                st.error("🚨 Yetkisiz Erişim Denemesi: Kullanıcı adı veya şifre hatalı.")
                log_kaydet(kullanici, "Hatalı şifre denemesi.")
else:
    kolon1, kolon2 = st.columns([8, 2])
    with kolon1:
        st.title("✈️ EHMS - Karar Destek Paneli")
    with kolon2:
        st.write(f"👤 **{st.session_state.aktif_kullanici.upper()}**")
        st.write(f"🛡️ *{st.session_state.aktif_rol}*")
        if st.button("🚪 Çıkış Yap"):
            log_kaydet(st.session_state.aktif_kullanici, "Sistemden güvenli çıkış yaptı.")
            st.session_state.giris_yapildi = False
            st.rerun()
            
    st.markdown("---")
    
    st.sidebar.header("🗄️ Sistem Veritabanı")
    if st.sidebar.button("Geçmiş İş Emirlerini Görüntüle"):
        st.subheader("🗄️ Veritabanı Kayıtları: Geçmiş Acil İş Emirleri")
        try:
            gecmis_kayitlar = tum_is_emirlerini_getir()
            if gecmis_kayitlar.empty:
                st.info("Veritabanında henüz kayıtlı bir iş emri bulunmamaktadır.")
            else:
                st.dataframe(gecmis_kayitlar, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Veritabanı okuma hatası: {e}")

    if st.session_state.aktif_rol == "Sistem Yöneticisi":
        if st.sidebar.button("🛡️ Güvenlik Loglarını İncele"):
            st.subheader("🛡️ Sistem Güvenlik ve İşlem Günlüğü (Audit Logs)")
            try:
                log_kayitlari = tum_loglari_getir()
                st.dataframe(log_kayitlari, use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(f"Log okuma hatası: {e}")
                
        # HATALI KISIM DÜZELTİLDİ: Kullanıcı ekleme paneli buradan tamamen kaldırıldı.

    st.sidebar.markdown("---")
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
            log_kaydet(st.session_state.aktif_kullanici, f"Motor {secilen_motor} için canlı telemetri simülasyonunu başlattı.")
            st.subheader(f"📡 Motor {secilen_motor} - Canlı Uçuş Telemetrisi (REST API Bağlantılı)")
            motor_verisi = df_test[df_test['Motor_ID'] == secilen_motor].copy()
            
            tablo_alani = st.empty()
            uyari_alani = st.empty()
            gecmis_veriler = pd.DataFrame()
            kritik_seviye_goruldu = False
            son_durum = {}
            
            for index, row in motor_verisi.iterrows():
                ham_tum_degerler = row[ozellik_sutunlari].values.tolist()
                
                try:
                    payload = {"tum_degerler": ham_tum_degerler}
                    api_cevap = requests.post("http://127.0.0.1:8000/tahmin/rul", json=payload)
                    
                    if api_cevap.status_code == 200:
                        veri = api_cevap.json()
                        anlik_rul = veri["kalan_omur_rul"]
                        kaynak = veri["ariza_kaynagi"]
                        zorluk = veri["ucus_profili"]
                    else:
                        st.error("API'den hatalı veri döndü.")
                        break
                except Exception as e:
                    st.error(f"API Sunucusuna Bağlanılamadı! Hata: {e}")
                    break
                
                yeni_satir = {
                    'Zaman Döngüsü': int(row['Zaman_Dongusu']),
                    'Anlık RUL': anlik_rul,
                    'Olası Arıza Kaynağı': kaynak,
                    'Uçuş Profili': zorluk
                }
                
                gecmis_veriler = pd.concat([gecmis_veriler, pd.DataFrame([yeni_satir])], ignore_index=True)
                
                with tablo_alani:
                    st.dataframe(gecmis_veriler.tail(8).style.map(durum_renklendir, subset=['Anlık RUL']), use_container_width=True, hide_index=True)
                
                if anlik_rul < 50:
                    kritik_seviye_goruldu = True
                    son_durum = yeni_satir
                    
                time.sleep(0.2)
                
            st.success(f"Motor {secilen_motor} için telemetri akışı bitti.")
            
            if kritik_seviye_goruldu:
                with uyari_alani:
                    rapor_metni = is_emri_olustur(secilen_motor, son_durum['Zaman Döngüsü'], son_durum['Anlık RUL'], son_durum['Olası Arıza Kaynağı'], son_durum['Uçuş Profili'])
                    try:
                        is_emri_kaydet(secilen_motor, son_durum['Anlık RUL'], son_durum['Olası Arıza Kaynağı'], son_durum['Uçuş Profili'], st.session_state.aktif_kullanici)
                        log_kaydet(st.session_state.aktif_kullanici, f"Motor {secilen_motor} için otonom acil bakım iş emri oluşturuldu.")
                        st.error("⚠️ KRİTİK UYARI: Uçuş sırasında motor ömrü 50'nin altına düştü! (Kayıt Veritabanına İşlendi)")
                    except Exception as e:
                        st.error(f"Kayıt Hatası: {e}")
                        
                    st.download_button("📄 İş Emrini İndir", data=rapor_metni, file_name=f"Acil_Bakim_Motor_{secilen_motor}.txt", mime="text/plain")