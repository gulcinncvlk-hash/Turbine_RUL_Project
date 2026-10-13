import sqlite3
import pandas as pd
from datetime import datetime

def veritabani_kur():
    conn = sqlite3.connect("ehms_sistem.db")
    cursor = conn.cursor()
    
    # 1. İş Emirleri Tablosu (Genişletildi: 'durum' eklendi)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS IsEmirleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            motor_id INTEGER,
            kalan_omur INTEGER,
            ariza_kaynagi TEXT,
            ucus_profili TEXT,
            onaylayan_yetkili TEXT,
            tarih TEXT,
            durum TEXT DEFAULT 'AÇIK'
        )
    ''')
    
    # 2. YENİ: Kullanıcılar Tablosu (Şifreler artık kodda değil, burada duracak)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Kullanicilar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kullanici_adi TEXT UNIQUE,
            sifre TEXT,
            rol TEXT
        )
    ''')
    
    # 3. YENİ: Sistem Logları Tablosu (Kimlik denetimi ve güvenlik takibi için)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS SistemLoglari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kullanici TEXT,
            islem TEXT,
            tarih TEXT
        )
    ''')
    
    # Varsayılan personeli veritabanına ekle (Eğer tablo boşsa bir defaya mahsus ekler)
    cursor.execute("SELECT COUNT(*) FROM Kullanicilar")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO Kullanicilar (kullanici_adi, sifre, rol) VALUES ('basmuhendis', 'tusas2026', 'Sistem Yöneticisi')")
        cursor.execute("INSERT INTO Kullanicilar (kullanici_adi, sifre, rol) VALUES ('teknisyen', 'bakim123', 'Saha Görevlisi')")
        
    conn.commit()
    conn.close()

# YENİ: Veritabanı üzerinden güvenli giriş kontrolü
def kullanici_dogrula(kullanici_adi, sifre):
    conn = sqlite3.connect("ehms_sistem.db")
    cursor = conn.cursor()
    # SQL sorgusu ile kullanıcıyı veritabanında arıyoruz
    cursor.execute("SELECT rol FROM Kullanicilar WHERE kullanici_adi=? AND sifre=?", (kullanici_adi, sifre))
    sonuc = cursor.fetchone()
    conn.close()
    
    if sonuc:
        return True, sonuc[0] # Giriş başarılı, kullanıcının rolünü (Örn: Sistem Yöneticisi) döndür
    return False, None

# YENİ: Sistemdeki her tıklamayı ve girişi kaydeden güvenlik günlüğü
def log_kaydet(kullanici, islem):
    conn = sqlite3.connect("ehms_sistem.db")
    cursor = conn.cursor()
    tarih = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO SistemLoglari (kullanici, islem, tarih) VALUES (?, ?, ?)", (kullanici, islem, tarih))
    conn.commit()
    conn.close()

def is_emri_kaydet(motor_id, rul, ariza_kaynagi, ucus_profili, yetkili):
    conn = sqlite3.connect("ehms_sistem.db")
    cursor = conn.cursor()
    tarih = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # İş emri oluşturulduğunda varsayılan durum 'AÇIK' olarak kaydedilir
    cursor.execute('''
        INSERT INTO IsEmirleri (motor_id, kalan_omur, ariza_kaynagi, ucus_profili, onaylayan_yetkili, tarih, durum)
        VALUES (?, ?, ?, ?, ?, ?, 'AÇIK')
    ''', (int(motor_id), int(rul), str(ariza_kaynagi), str(ucus_profili), str(yetkili), tarih))
    
    conn.commit()
    conn.close()

def tum_is_emirlerini_getir():
    conn = sqlite3.connect("ehms_sistem.db")
    veriler = pd.read_sql_query("SELECT id, motor_id, kalan_omur, ariza_kaynagi, ucus_profili, durum, onaylayan_yetkili, tarih FROM IsEmirleri ORDER BY id DESC", conn)
    conn.close()
    return veriler

# YENİ: Başmühendisin güvenlik loglarını çekmesi için fonksiyon
def tum_loglari_getir():
    conn = sqlite3.connect("ehms_sistem.db")
    veriler = pd.read_sql_query("SELECT * FROM SistemLoglari ORDER BY id DESC", conn)
    conn.close()
    return veriler