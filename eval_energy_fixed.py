import pandas as pd
import numpy as np
import time
import json
import warnings
warnings.filterwarnings('ignore')
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor

RANDOM_STATE = 42
np.random.seed(RANDOM_STATE)

CONFIG = {'csv_path': 'sensor_data.csv', 'sample_fraction': 1.0, 'chunksize': 200_000,
          'train_size': 0.8, 'rolling_window_short': 100, 'rolling_window_long': 300}

print('='*70)
print('ENERGY PREDICTION MODELS — VALIDASI AKURASI (FIXED SHIFT(1))')
print('='*70)

# Load
print('\nLoading CSV...')
t0 = time.time()
chunks = []
total_read = 0
for chunk in pd.read_csv(CONFIG['csv_path'], chunksize=CONFIG['chunksize']):
    chunk = chunk.rename(columns={'Timestamp':'timestamp','DeviceID':'device_id',
        'Suhu (C)':'suhu','Kelembaban (%)':'kelembaban','Tegangan (V)':'tegangan',
        'Arus (A)':'arus','Daya (W)':'daya','Jumlah Orang':'jumlah_orang'})
    chunks.append(chunk)
    total_read += len(chunk)
df = pd.concat(chunks, ignore_index=True)
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)
df = df.dropna(subset=['suhu','kelembaban','tegangan','arus','daya','jumlah_orang'])
print(f'Loaded {len(df):,} records in {time.time()-t0:.1f}s')

# Feature engineering
print('\nFeature engineering...')
df['tegangan_arus'] = df['tegangan'] * df['arus']
df['suhu_kelembaban'] = df['suhu'] * df['kelembaban']
df['hour'] = df['timestamp'].dt.hour
df['dayofweek'] = df['timestamp'].dt.dayofweek
df['day'] = df['timestamp'].dt.day

def categorize_time(h):
    if 6<=h<10: return 'morning'
    elif 10<=h<14: return 'midday'
    elif 14<=h<18: return 'afternoon'
    elif 18<=h<22: return 'evening'
    else: return 'night'
df['time_period'] = df['hour'].apply(categorize_time)
df = pd.get_dummies(df, columns=['time_period'], drop_first=False)
time_period_cols = [c for c in df.columns if c.startswith('time_period_')]

static_feature_columns = ['suhu','kelembaban','tegangan','arus','jumlah_orang',
    'tegangan_arus','suhu_kelembaban','hour','dayofweek','day'] + time_period_cols
y = df['daya'].values

# Train-test split CHRONOLOGICAL
train_size = int(len(df) * CONFIG['train_size'])
df_train = df.iloc[:train_size].copy()
df_test = df.iloc[train_size:].copy()
y_train = y[:train_size]
y_test = y[train_size:]
print(f'\nTrain: {len(df_train):,}, Test: {len(df_test):,}')

# === ROLLING MEANS WITH .shift(1) ===
ws = CONFIG['rolling_window_short']
wl = CONFIG['rolling_window_long']
for d in (df_train, df_test):
    d['daya_ma_short'] = d['daya'].shift(1).rolling(window=ws, min_periods=1).mean()
    d['daya_ma_long'] = d['daya'].shift(1).rolling(window=wl, min_periods=1).mean()
    d['suhu_ma_short'] = d['suhu'].shift(1).rolling(window=ws, min_periods=1).mean()

feature_columns = static_feature_columns + ['daya_ma_short','daya_ma_long','suhu_ma_short']
print(f'Total features: {len(feature_columns)}')

X_train = df_train[feature_columns].fillna(0).values
X_test = df_test[feature_columns].fillna(0).values
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Evaluate function
def evaluate_all(name, y_tr, y_te, y_pred_tr, y_pred_te):
    rmse_te = np.sqrt(mean_squared_error(y_te, y_pred_te))
    mae_te = mean_absolute_error(y_te, y_pred_te)
    r2_te = r2_score(y_te, y_pred_te)
    r2_tr = r2_score(y_tr, y_pred_tr)
    mask = y_te != 0
    mape_te = np.mean(np.abs((y_te[mask] - y_pred_te[mask]) / y_te[mask])) * 100
    adj_r2_te = 1 - (1-r2_te)*(len(y_te)-1)/(len(y_te)-len(feature_columns)-1)
    explained_var = 1 - np.var(y_te - y_pred_te)/np.var(y_te)
    med_abs_err = np.median(np.abs(y_te - y_pred_te))
    bias = np.mean(y_pred_te - y_te)
    return {'model':name, 'rmse':rmse_te, 'mae':mae_te, 'r2':r2_te, 'mape':mape_te,
            'r2_train':r2_tr, 'adj_r2':adj_r2_te, 'explained_variance':explained_var,
            'median_abs_error':med_abs_err, 'bias':bias}

results = []

# Model 1: Linear Regression
print('\n[1] Linear Regression...')
t0 = time.time()
lr = LinearRegression()
lr.fit(X_train_scaled, y_train)
lr_pred_te = lr.predict(X_test_scaled)
lr_pred_tr = lr.predict(X_train_scaled)
lr_time = time.time() - t0
res = evaluate_all('Linear Regression', y_train, y_test, lr_pred_tr, lr_pred_te)
res['train_time'] = lr_time
results.append(res)
print(f'  R2_train={res["r2_train"]:.4f}, R2_test={res["r2"]:.4f}, RMSE={res["rmse"]:.3f}')

# Model 2: Random Forest
print('\n[2] Random Forest...')
t0 = time.time()
rf = RandomForestRegressor(n_estimators=100, max_depth=15, min_samples_split=5,
    min_samples_leaf=2, random_state=RANDOM_STATE, n_jobs=-1)
rf.fit(X_train, y_train)
rf_pred_te = rf.predict(X_test)
rf_pred_tr = rf.predict(X_train)
rf_time = time.time() - t0
res = evaluate_all('Random Forest', y_train, y_test, rf_pred_tr, rf_pred_te)
res['train_time'] = rf_time
results.append(res)
print(f'  R2_train={res["r2_train"]:.4f}, R2_test={res["r2"]:.4f}, RMSE={res["rmse"]:.3f}')

# Print summary table
print(f'\n{"="*70}')
print('RESULTS COMPARISON: BEFORE vs AFTER shift(1) fix')
print(f'{"="*70}')
print(f'{"Model":<20} {"R2_before":>12} {"R2_after":>12} {"dR2":>10} {"RMSE_after":>12} {"MAE_after":>10}')
print('-'*70)
for r in results:
    if r['model'] == 'Linear Regression':
        print(f'{r["model"]:<20} {0.9629:>12.4f} {r["r2"]:>12.4f} {r["r2"]-0.9629:>10.4f} {r["rmse"]:>12.3f} {r["mae"]:>10.3f}')
    elif r['model'] == 'Random Forest':
        print(f'{r["model"]:<20} {0.9952:>12.4f} {r["r2"]:>12.4f} {r["r2"]-0.9952:>10.4f} {r["rmse"]:>12.3f} {r["mae"]:>10.3f}')

print(f'\nInterpretasi:')
for r in results:
    gap = abs(r['r2_train'] - r['r2'])
    if gap > 0.1:
        print(f'  {r["model"]}: GAP {gap:.4f} -> OVERFITTING terdeteksi')
    elif gap > 0.05:
        print(f'  {r["model"]}: GAP {gap:.4f} -> slight overfitting')
    else:
        print(f'  {r["model"]}: GAP {gap:.4f} -> baik, tidak overfit')

# Save results
with open('energy_model_results_fixed.json', 'w') as f:
    json.dump(results, f, indent=2, default=float)
print(f'\nSaved: energy_model_results_fixed.json')
