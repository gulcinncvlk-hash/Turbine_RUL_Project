import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error
import joblib

def veri_yukle_ve_rul_hesapla(dosya_yolu):
    sutunlar = ['Motor_ID', 'Zaman_Dongusu', 'Op_Ayar_1', 'Op_Ayar_2', 'Op_Ayar_3'] + [f'Sensor_{i}' for i in range(1, 22)]
    df = pd.read_csv(dosya_yolu, sep=r"\s+", header=None, names=sutunlar)
    
    # Her motor için maksimum zaman döngüsünü (ömrünü) bul
    maks_dongu = df.groupby('Motor_ID')['Zaman_Dongusu'].max()
    
    # RUL (Kalan Faydalı Ömür) hesapla
    df['RUL'] = df.apply(lambda row: maks_dongu[row['Motor_ID']] - row['Zaman_Dongusu'], axis=1)
    
    # Havacılık endüstrisi standardı: RUL değerini 130 ile sınırla (Piecewise Linear Degradation)
    # Erken döngülerde aşınma logaritmik olmadığı için 130 üstü sabit kabul edilir.
    df['RUL'] = df['RUL'].clip(upper=130)
    
    return df

print("1. NASA CMAPSS Veri Setleri (FD001, FD002, FD003, FD004) Yükleniyor...")
df_fd001 = veri_yukle_ve_rul_hesapla('train_FD001.txt')
df_fd002 = veri_yukle_ve_rul_hesapla('train_FD002.txt')
df_fd003 = veri_yukle_ve_rul_hesapla('train_FD003.txt')
df_fd004 = veri_yukle_ve_rul_hesapla('train_FD004.txt')

# Tüm veri setlerini tek bir büyük veri havuzunda birleştir
df_tum_veriler = pd.concat([df_fd001, df_fd002, df_fd003, df_fd004], ignore_index=True)
print(f"Toplam Veri Satırı: {len(df_tum_veriler)}")

# Özellik Mühendisliği (Feature Engineering)
# Tüm operasyonel ayarlar ve sensörler eğitime dahil ediliyor. 
# Sabit olan sensörler model tarafından otomatik elenecektir.
ozellik_sutunlari = ['Op_Ayar_1', 'Op_Ayar_2', 'Op_Ayar_3'] + [f'Sensor_{i}' for i in range(1, 22)]
X = df_tum_veriler[ozellik_sutunlari]
y = df_tum_veriler['RUL']

print("2. Veriler Ölçeklendiriliyor (StandardScaler)...")
scaler = StandardScaler()
X_olcekli = scaler.fit_transform(X)

print("3. XGBoost v2 Yapay Zeka Modeli Eğitiliyor (Bu işlem bilgisayar gücüne göre 1-2 dakika sürebilir)...")
model = xgb.XGBRegressor(
    n_estimators=150, 
    max_depth=6, 
    learning_rate=0.1, 
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42
)
model.fit(X_olcekli, y)

# Eğitim başarısını ölç
tahminler = model.predict(X_olcekli)
rmse = np.sqrt(mean_squared_error(y, tahminler))
print(f"Eğitim Tamamlandı! Kök Ortalama Kare Hata (RMSE): {rmse:.2f}")

print("4. Yeni Model ve Ölçeklendirici Dosyalara Kaydediliyor...")
joblib.dump(model, 'xgboost_rul_modeli_v2.joblib')
joblib.dump(scaler, 'veri_olceklendirici_v2.joblib')
joblib.dump(ozellik_sutunlari, 'ozellik_sutunlari_v2.joblib')

print("BÜTÜN İŞLEMLER BAŞARIYLA TAMAMLANDI. V2 DOSYALARI KULLANIMA HAZIR.")