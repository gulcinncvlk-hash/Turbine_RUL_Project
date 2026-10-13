from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
import pandas as pd
import numpy as np

app = FastAPI(title="EHMS Backend Sunucusu", version="2.0")

try:
    model = joblib.load('xgboost_rul_modeli_v2.joblib')
    scaler = joblib.load('veri_olceklendirici_v2.joblib')
    ozellik_sutunlari = joblib.load('ozellik_sutunlari_v2.joblib')
except Exception as e:
    print(f"Hata: {e}")

ALT_SISTEMLER = {
    'Yüksek Basınç Kompresörü (HPC)': ['Sensor_3', 'Sensor_7', 'Sensor_11', 'Sensor_17'],
    'Türbin Modülü (HPT/LPT)': ['Sensor_4', 'Sensor_20', 'Sensor_21'],
    'Fan ve Bypass Kanalı': ['Sensor_2', 'Sensor_8', 'Sensor_13', 'Sensor_15'],
    'Çekirdek Motor / Yanma Odası': ['Sensor_9', 'Sensor_12', 'Sensor_14']
}

# YENİ: Arayüzden artık ayrı ayrı değil, tek parça (24 özellik) veri gelecek
class TelemetriVerisi(BaseModel):
    tum_degerler: list[float]

def ariza_kaynagi_bul(olcekli_veri_satiri, ozellik_isimleri):
    degerler = dict(zip(ozellik_isimleri, olcekli_veri_satiri))
    en_riskli_sistem = "Normal"
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

@app.post("/tahmin/rul")
def rul_tahmin_et(veri: TelemetriVerisi):
    try:
        # Gelen 24'lü paketi doğrudan modele sokuyoruz
        X_anlik = np.array(veri.tum_degerler).reshape(1, -1)
        X_anlik_olcekli = scaler.transform(pd.DataFrame(X_anlik, columns=ozellik_sutunlari))
        
        tahmini_rul = int(model.predict(X_anlik_olcekli)[0])
        
        kaynak = "Normal" if tahmini_rul > 100 else ariza_kaynagi_bul(X_anlik_olcekli[0], ozellik_sutunlari)
        # İlk 3 sütun Op_Ayar_1, 2, 3 olduğu için doğrudan indeksten çekiyoruz
        zorluk = ucus_zorlugu_hesapla(X_anlik[0][0], X_anlik[0][1], X_anlik[0][2])
        
        return {
            "durum": "basarili", 
            "kalan_omur_rul": tahmini_rul,
            "ariza_kaynagi": kaynak,
            "ucus_profili": zorluk
        }
    except Exception as e:
        print(f"API Çökme Nedeni: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))