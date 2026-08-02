# Audit Kesesuaian Referensi

Tanggal audit: 29 Juli 2026
Jumlah PDF yang diperiksa: **30**

## 1. Ruang lingkup dan notasi

Audit dilakukan terhadap unsur pokok judul dan dimensi pendukung ruang
lingkup penelitian:

- **EC:** arsitektur edge, fog, dan/atau cloud;
- **E:** monitoring daya atau energi bangunan;
- **O:** monitoring okupansi;
- **N:** pemrosesan near real-time, streaming, atau pengukuran latensi;
- **G-I:** visualisasi geospasial–indoor, BIM–GIS, atau multiskala;
- **DT:** Digital Twin, digital shadow, BIM, atau Web-3D;
- **R:** replay data historis atau evaluasi berbasis trace.

Notasi pada matriks: **✓** = dibahas langsung; **△** = dibahas sebagian atau
sebagai konteks; **–** = tidak dibahas.

Tier tidak sama dengan peringkat mutu jurnal. Tier menunjukkan kesesuaian
referensi terhadap penelitian ini:

- **T1:** sumber inti yang dapat dipakai langsung;
- **T2:** sumber pendukung atau sumber yang perlu verifikasi silang;
- **T3:** arsip; tidak disarankan sebagai dasar klaim utama.

## 2. Temuan utama

Koleksi sekarang cukup kuat untuk menjelaskan arsitektur edge-cloud,
pemrosesan stream, Digital Twin bangunan, energi–okupansi, serta visualisasi
BIM–GIS indoor–outdoor secara terpisah. Lima tambahan open-access menutup
kesenjangan yang sebelumnya paling besar pada okupansi dan visual multiskala.
Tidak ada satu artikel yang menggabungkan ketujuh unsur dalam eksperimen yang
sama; sintesis pustaka tetap harus dibangun per rumpun.

Klaim Digital Twin perlu dibatasi secara konsisten. Bila data hanya mengalir
dari sensor atau replay menuju model Web-3D tanpa mekanisme kendali balik ke
aset fisik, istilah yang paling aman adalah **digital shadow**, **visualisasi
Digital Twin**, atau **Digital Twin satu arah**, bukan Digital Twin
bidireksional penuh.

## 3. Matriks 25 PDF awal

Kolom **P** pada tabel awal setara dengan **E** pada notasi terbaru. Tabel
dipertahankan agar audit terdahulu dapat ditelusuri; dimensi okupansi dan
geospasial–indoor untuk lima tambahan diaudit pada Bagian 4.

| No. | File | Publikasi dan DOI | Tier | EC | P | N | DT | R | Penggunaan dan kehati-hatian |
|---:|---|---|:---:|:---:|:---:|:---:|:---:|:---:|---|
| 1 | `14_Real-Time_Safety_Monitoring_System_for_Smart_Const.pdf` | Chen & Zheng, ACM ICAISM (2025); `10.1145/3756423.3756551` | T3 | ✓ | – | ✓ | △ | – | Domainnya keselamatan konstruksi, bukan daya bangunan. Jangan gunakan sebagai sumber utama; beberapa DOI pada daftar pustakanya tidak sesuai dengan judul yang dikutip dan satu DOI tampak seperti placeholder. |
| 2 | `18_Exploring_the_Synergy_of_Advanced_Lighting_Control.pdf` | Zocchi dkk., *Sustainability* 16 (2024), 10937; `10.3390/su162410937` | T2 | – | ✓ | △ | △ | – | Tinjauan sistematis tentang kontrol pencahayaan, BIM, dan IoT. Berguna untuk konteks efisiensi pencahayaan, tetapi bukan bukti arsitektur atau replay. |
| 3 | `20_Intelligent_Energy_Consumption_For_Smart_Homes_Usi.pdf` | AlZaabi dkk., *Computers, Materials & Continua* (2023); `10.32604/cmc.2023.031834` | T3 | △ | ✓ | – | – | – | Fokus prediksi konsumsi dengan machine learning dan pelaporan akurasi 92,3%; tidak sesuai dengan fokus pemantauan/replay near real-time. |
| 4 | `37_Smart_Digital_Twin_for_Energy_Efficiency_in_Buildi.pdf` | Suharto dkk., *E3S Web of Conferences* 687 (2026), 02006; `10.1051/e3sconf/202668702006` | T3 | – | ✓ | △ | – | △ | Nama file menyesatkan: isi utamanya prediksi LSTM–GNN memakai data historis publik, bukan implementasi Digital Twin. |
| 5 | `A_Fog_Computing_DataManagement_SmartHome.pdf` | Lawal dkk., LNNS (2022); `10.1007/978-3-031-18458-1_17` | T1 | ✓ | △ | ✓ | – | – | Mendukung pembagian kerja fog/cloud dan evaluasi latensi, tetapi eksperimennya simulasi CCTV smart-home dan “energi” mengacu pada komputasi, bukan daya bangunan. |
| 6 | `Cognitive_DigitalTwins_Climate_Resilient_Buildings.pdf` | Samaei & Riffat (2026); `10.65582/aifsc.2026.005` | T2 | – | ✓ | ✓ | ✓ | – | Mendukung konsep Digital Twin untuk HVAC/kendali iklim; simulatif dan berasal dari outlet baru, sehingga klaim perlu diperkuat sumber lain. |
| 7 | `Edge_Computing_Optimizing_SensorData_SmartBuildings.pdf` | Fajri dkk., *JICS* 4(2) (2025); `10.56347/jics.v4i2.369` | T1 | ✓ | △ | ✓ | – | – | Eksperimen laboratorium membandingkan edge dan cloud; melaporkan penurunan latensi 79,8%, kenaikan throughput 37%, dan pengurangan bandwidth 50%. Gunakan untuk pola evaluasi, bukan generalisasi universal. |
| 8 | `Elsevier_Building_and_Environment_2024_111355.pdf` | Sun, *Building and Environment* (2024), 111355; `10.1016/j.buildenv.2024.111355` | T3 | – | △ | – | – | △ | Pemodelan okupansi berbasis Transformer. Data historisnya dapat memberi konteks ML, tetapi target dan metode tidak sesuai dengan pemantauan daya edge-cloud. |
| 9 | `Huang_2025_RealTime_Energy_Management_Edge.pdf` | Huang dkk., *Scientific Reports* (2025); `10.1038/s41598-025-07592-4` | T2 | ✓ | ✓ | ✓ | – | △ | Sangat dekat dengan edge dan manajemen energi real-time, namun beberapa judul/rujukan internal tidak berhasil ditelusuri secara meyakinkan. Jangan jadikan satu-satunya dasar klaim. |
| 10 | `Hybrid_EdgeCloud_EnergyEfficiency_Buildings.pdf` | Himeur dkk., IntelliSys/LNNS (2021); `10.1007/978-3-030-82196-8_6` | T1 | ✓ | ✓ | ✓ | – | – | Referensi langsung untuk alasan memilih arsitektur hibrida edge-cloud pada bangunan. Berupa bab prosiding, bukan artikel jurnal. |
| 11 | `ICAIS2021_FederatedLearning_SmartBuildings.pdf` | Mitra dkk., IEEE ICAIS (2021); `10.1109/ICAIS50930.2021.9395938` | T3 | ✓ | △ | △ | – | – | Fokus federated learning dan privasi. Tidak diperlukan untuk metode replay/pemantauan saat ini kecuali federated learning benar-benar diterapkan. |
| 12 | `Informatica_2025_SmartBuilding_SensorData.pdf` | Deng, *Informatica* 49(28) (2025); `10.31449/inf.v49i28.10300` | T3 | △ | △ | ✓ | ✓ | – | Studi stadion dan diffusion model, bukan pemantauan daya. Ada inkonsistensi nama penulis pada header halaman; verifikasi bibliografi sebelum mengutip. |
| 13 | `MDPI_Applications_DataAnalytics_IoT_Edge.pdf` | Rojek dkk., *Applied Sciences* 16 (2026), 225; `10.3390/app16010225` | T2 | ✓ | ✓ | ✓ | △ | – | Tinjauan luas IoT, edge, dan analitik energi; cocok untuk latar belakang, bukan bukti eksperimen proyek. |
| 14 | `MDPI_Buildings_DigitalShadow_Definition.pdf` | Sepasgozar, *Buildings* 11 (2021), 151; `10.3390/buildings11040151` | T1 | – | △ | ✓ | ✓ | – | Sumber penting untuk membedakan digital model, digital shadow, dan Digital Twin berdasarkan arah aliran data. Gunakan untuk membatasi nomenklatur sistem. |
| 15 | `MDPI_Buildings_DigitalTwins_BuildingEnergy.pdf` | Sghiri dkk., *Buildings* 15 (2025), 498; `10.3390/buildings15030498` | T1 | △ | ✓ | ✓ | ✓ | – | Tinjauan langsung tentang Digital Twin untuk energi bangunan; baik untuk sintesis state of the art, tetapi bukan validasi implementasi sendiri. |
| 16 | `MDPI_Buildings_EnergyManagement_Systems.pdf` | Shahid dkk., *Buildings* 15 (2025), 4237; `10.3390/buildings15234237` | T1 | △ | ✓ | △ | △ | – | Mendukung konteks sistem manajemen energi bangunan dan teknologi pendukung; sifatnya tinjauan. |
| 17 | `MDPI_Electronics_Web3D_DigitalTwin.pdf` | Sinthamrongruk dkk., *Electronics* 15 (2026), 1736; `10.3390/electronics15081736` | T1 | △ | ✓ | ✓ | ✓ | – | Sumber paling dekat untuk Web-3D: deployment 12 bulan, 60 sensor, 66 FPS, latensi 78 ms, dan reliabilitas sekitar 98%. Periksa definisi setiap metrik sebelum membandingkan hasil. |
| 18 | `MDPI_Energies_Transformer_EnergyPrediction.pdf` | Moveh dkk., *Energies* 18 (2025), 1468; `10.3390/en18061468` | T3 | – | ✓ | – | – | △ | Fokus prediksi energi berbasis Transformer, bukan pemantauan daya atau pemrosesan edge-cloud. |
| 19 | `MDPI_FutureInternet_CloudComputing_Cities.pdf` | Trigka & Dritsas, *Future Internet* 17 (2025), 118; `10.3390/fi17030118` | T1 | ✓ | △ | ✓ | △ | – | Berguna untuk landasan arsitektur cloud/edge pada smart city dan integrasi data, tetapi merupakan tinjauan umum. |
| 20 | `MDPI_Mathematics_AIoT_DigitalTwin_Survey.pdf` | Luo dkk., *Mathematics* 13 (2025), 3382; `10.3390/math13213382` | T3 | △ | – | △ | ✓ | – | Survei AIoT/Digital Twin generatif terlalu luas dan tidak mendukung langsung daya bangunan atau replay. |
| 21 | `MDPI_Sensors_BuildingModelManagement.pdf` | Wang dkk., *Sensors* 25 (2025), 6069; `10.3390/s25196069` | T1 | △ | △ | ✓ | ✓ | – | Implementasi MQTT over WebSocket dan Three.js dengan latensi sekitar 280–550 ms; kuat untuk desain integrasi Web-3D near real-time. |
| 22 | `Raith_2023_FaaS_Sim_Trace_Driven_Edge_Cloud.pdf` | Raith dkk., *Software: Practice and Experience* (2023); `10.1002/spe.3277` | T1 | ✓ | – | ✓ | – | ✓ | Sumber terkuat di koleksi untuk metodologi simulasi/evaluasi edge-cloud berbasis trace. Tidak spesifik bangunan, sehingga perlu dipasangkan dengan referensi energi bangunan. |
| 23 | `Xhafa_2020_IoT_Stream_Processing_Edge.pdf` | Xhafa dkk., *Future Generation Computer Systems* (2020); `10.1016/j.future.2019.12.031` | T1 | ✓ | – | ✓ | – | △ | Menguji pemrosesan stream IoT dengan trace sensor nyata, Raspberry Pi, dan Node-RED serta metrik RTT, laju, dan memori. Bukan replay bangunan secara eksplisit. |
| 24 | `Marquez_Sanchez_2023_Adaptive_Edge_BEMS.pdf` | Márquez-Sánchez dkk., *Electronics* 12 (2023), 4179; `10.3390/electronics12194179` | T1 | ✓ | ✓ | ✓ | – | – | Sumber langsung untuk arsitektur BEMS tiga lapis IoT–edge–cloud: smart meter, MQTT, Jetson Nano, dan AWS. Mendukung pemantauan real-time, tetapi tidak melaporkan benchmark latensi kuantitatif dan penerapan lapangan yang lebih luas masih dinyatakan sebagai pekerjaan lanjutan. |
| 25 | `Lu_2020_Digital_Twin_Asset_Monitoring.pdf` | Lu dkk., *Automation in Construction* 118 (2020), 103277; `10.1016/j.autcon.2020.103277` | T1 | – | △ | ✓ | ✓ | △ | Studi kasus monitoring kontinu pompa HVAC berbasis IFC dan Bayesian online change-point detection pada fasilitas West Cambridge. Kuat untuk integrasi data operasional/historis dalam DT, tetapi bukan arsitektur edge-cloud, bukan Web-3D, dan tidak melakukan replay data. File lokal merupakan accepted manuscript resmi Cambridge. |

## 4. Lima referensi baru dan fungsi klaim

| No. | File | Publikasi dan DOI | Tier | EC | E | O | N | G-I | DT | R | Penggunaan dan kehati-hatian |
|---:|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| 26 | `Chen_2021_BIM_GIS_Indoor_Outdoor_Visualization.pdf` | Chen, Chen, & Huang, *ISPRS IJGI* 10 (2021), 756; `10.3390/ijgi10110756` | T1 | – | – | – | △ | ✓ | ✓ | – | Dasar langsung untuk visualisasi BIM skala besar dalam konteks indoor–outdoor dan lingkungan geografis multiskala. Hasil frame-rate artikel tidak boleh disamakan dengan dashboard proyek karena kompleksitas model dan perangkat berbeda. |
| 27 | `Herle_2020_GIM_BIM_Interoperability.pdf` | Herle dkk., *PFG* 88 (2020), 33–42; `10.1007/s41064-020-00090-4` | T1 | – | – | – | – | ✓ | △ | – | Menjelaskan perbedaan dan interoperabilitas geospatial information modelling dengan BIM. Cocok untuk fondasi konsep tapak–bangunan, bukan bukti bahwa implementasi proyek sudah patuh IFC/CityGML. |
| 28 | `Smirnov_2026_Occupancy_Aware_DT.pdf` | Smirnov & Re Cecconi, *Buildings* 16 (2026), 1629; `10.3390/buildings16081629` | T1 | △ | ✓ | ✓ | ✓ | △ | ✓ | △ | Menghubungkan Digital Twin, energi, okupansi, dan visualisasi pada 26 ruang kantor. Metode inferensi CO₂ serta metrik akurasinya tidak dipindahkan ke proyek; kolom `people_count` proyek tetap data historis legacy. |
| 29 | `Clausen_2021_DT_Energy_Comfort.pdf` | Clausen dkk., *Energy Informatics* 4 (2021), 40; `10.1186/s42162-021-00153-9` | T1 | △ | ✓ | ✓ | ✓ | △ | ✓ | – | Kerangka Digital Twin memakai okupansi, keadaan ruang, dan kendali untuk energi/kenyamanan. Dipakai untuk hubungan konseptual energi–okupansi serta untuk menunjukkan bahwa proyek saat ini belum memiliki kendali balik. |
| 30 | `Walczyk_2024_BIM_DT_Distributed_IoT.pdf` | Walczyk & Ożadowicz, *Future Internet* 16 (2024), 225; `10.3390/fi16070225` | T1 | ✓ | ✓ | ✓ | ✓ | △ | ✓ | – | Tinjauan terarah BIM, Digital Twin, otomasi bangunan, IoT terdistribusi, dan efisiensi energi. Dipakai sebagai peta teknologi; bukan bukti hasil eksperimen proyek. |

Kelima file telah diverifikasi dengan metadata PDF lokal (`pdfinfo`) dan teks
halaman awal. Seluruhnya merupakan artikel open-access dari laman penerbit.

## 5. Kesenjangan terhadap proyek

Koleksi masih memerlukan sumber yang lebih langsung untuk:

1. replay berjuta baris data sensor dengan jaminan urutan timestamp, laju replay,
   backpressure, dan reproduktibilitas;
2. pengukuran energi aktif bangunan pada perangkat edge dengan meter dan faktor
   daya terkalibrasi, bukan hanya integrasi proksi V×I;
3. pengukuran end-to-end pada Raspberry Pi, cloud publik, penyimpanan
   time-series, API, dan render browser dalam satu eksperimen;
4. pembatasan klaim antara data historis yang di-replay, emulasi jaringan, dan
   pengukuran lapangan/public cloud;
5. validasi koordinat tapak, transformasi CRS, hubungan semantik objek
   tapak–bangunan–ruang, dan kepatuhan terhadap standar geospasial/indoor;
6. validasi sensor okupansi legacy terhadap ground truth;
7. validasi Digital Twin bidireksional; apabila kendali balik tidak tersedia,
   penelitian harus secara eksplisit menyatakan implementasinya satu arah.

Tidak ada satu PDF saat ini yang sendirian membuktikan keseluruhan alur proyek.
Argumen penelitian harus dibangun dari gabungan sumber: arsitektur edge-cloud,
stream/replay, energi bangunan, serta Digital Twin/Web-3D.

## 6. Kandidat open-access yang sudah diverifikasi daring

Empat artikel berikut **belum tercatat sebagai PDF lokal dalam audit ini**.
Tautan diberikan sebagai calon unduhan dan harus diperiksa kembali metadata,
lisensi, serta isi PDF-nya setelah diunduh.

| ID | Kandidat dan DOI | Kesenjangan yang ditutup | Tautan PDF/akses |
|:---:|---|---|---|
| A | Verde Romero dkk., “An open source IoT edge-computing system for monitoring energy consumption in buildings,” *Results in Engineering* 21 (2024), 101875; `10.1016/j.rineng.2024.101875` | Pengukuran tegangan, arus, dan daya bangunan nyata; MQTT serta edge/fog. | [PDF penerbit](https://www.sciencedirect.com/science/article/pii/S2590123024001282/pdfft?isDTMRedir=true&download=true) |
| B | Ye dkk., “Efficient data replay mechanism of sensor stream data based on concurrent buffer pool,” *Journal of King Saud University – Computer and Information Sciences* 34 (2022), 10293–10303; `10.1016/j.jksuci.2022.10.021` | Replay jutaan data sensor, urutan data, dan pengaturan laju pemutaran. | [PDF penerbit](https://www.sciencedirect.com/science/article/pii/S131915782200372X/pdfft?isDTMRedir=true&download=true) |
| C | Eneyew, Capretz, & Bitsuamlak, “Toward Smart-Building Digital Twins: BIM and IoT Data Integration,” *IEEE Access* 10 (2022), 130487–130506; `10.1109/ACCESS.2022.3229370` | Arsitektur berlapis Digital Twin bangunan dan integrasi data time-series. | [PDF IEEE](https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=9987476) |
| D | Fatehi Karjou dkk., “Practical Design and Implementation of IoT-Based Occupancy Monitoring Systems for Office Buildings: A Case Study,” *Energy and Buildings* 323 (2024), 114852; `10.1016/j.enbuild.2024.114852` | Arsitektur IoT/cloud dan validasi okupansi pada ruang kantor nyata. | [PDF repositori RWTH](https://publications.rwth-aachen.de/record/994134/files/994134.pdf) |

Kandidat A–C tetap calon PDF lokal karena endpoint penerbit menolak unduhan
otomatis. Kandidat D telah diverifikasi sebagai PDF open-access 15 halaman
melalui repositori RWTH, tetapi proteksi JavaScript repositori mencegah salinan
otomatis yang dapat diaudit di folder lokal. Status ini dicatat agar tautan
daring tidak disalahartikan sebagai file lokal.

## 7. Rekomendasi penggunaan dalam naskah

- Gunakan `Hybrid_EdgeCloud_EnergyEfficiency_Buildings.pdf`,
  `Edge_Computing_Optimizing_SensorData_SmartBuildings.pdf`, dan
  `Xhafa_2020_IoT_Stream_Processing_Edge.pdf` untuk menjelaskan alasan serta
  metrik pembagian kerja edge-cloud.
- Gunakan `Raith_2023_FaaS_Sim_Trace_Driven_Edge_Cloud.pdf` sebagai dasar
  metodologis evaluasi berbasis trace/replay, lalu jelaskan bahwa trace proyek
  berasal dari data sensor historis bangunan.
- Gunakan `MDPI_Electronics_Web3D_DigitalTwin.pdf` dan
  `MDPI_Sensors_BuildingModelManagement.pdf` untuk lapisan Web-3D dan komunikasi
  near real-time.
- Gunakan `Marquez_Sanchez_2023_Adaptive_Edge_BEMS.pdf` untuk rancangan BEMS
  IoT–edge–cloud dan pemantauan daya, tetapi jangan mengutipnya sebagai bukti
  benchmark latensi lapangan.
- Gunakan `Lu_2020_Digital_Twin_Asset_Monitoring.pdf` untuk integrasi data
  operasional/historis dan monitoring kontinu berbasis DT, bukan sebagai dasar
  klaim replay atau Web-3D.
- Gunakan `MDPI_Buildings_DigitalShadow_Definition.pdf` untuk menyatakan secara
  jujur apakah implementasi merupakan Digital Twin bidireksional atau digital
  shadow satu arah.
- Gunakan `Chen_2021_BIM_GIS_Indoor_Outdoor_Visualization.pdf` dan
  `Herle_2020_GIM_BIM_Interoperability.pdf` untuk mendefinisikan perpindahan
  skala tapak–bangunan–indoor, tetapi jangan mengklaim kepatuhan standar yang
  belum diuji.
- Gunakan `Smirnov_2026_Occupancy_Aware_DT.pdf` dan
  `Clausen_2021_DT_Energy_Comfort.pdf` untuk membahas hubungan energi,
  okupansi, kenyamanan, dan Digital Twin. Jangan meminjam angka akurasi
  okupansi artikel sebagai hasil proyek.
- Gunakan `Walczyk_2024_BIM_DT_Distributed_IoT.pdf` untuk sintesis lapisan
  teknologi BIM–Digital Twin–IoT, bukan sebagai pengganti evaluasi kuantitatif.
- Jangan membandingkan angka latensi antarartikel tanpa menyamakan titik awal,
  titik akhir, perangkat, interval kirim, kondisi jaringan, dan statistik yang
  digunakan.
- Pisahkan dengan jelas hasil **replay lokal**, **emulasi jaringan**, dan
  **pengukuran lapangan/public cloud**. Ketiganya bukan bukti yang setara.
- Jangan menggunakan akurasi prediksi energi sebagai indikator keberhasilan
  pemantauan apabila penelitian final tidak lagi melatih model prediksi.

Lima PDF ditambahkan dan tidak ada PDF lama yang dihapus atau diubah dalam
proses audit dokumentasi ini.
