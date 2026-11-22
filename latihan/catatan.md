Sesi 1 bagian 1.1 
1. Apa itu tabel, kolom, dan record? 
2. Apa fungsi primary key? 
3. Apa fungsi NOT NULL dan UNIQUE?
4. Kenapa NIM disimpan sebagai TEXT, bukan INTEGER?
Jawab
1. Table adalah struktur yang menyimpan data sejenis, contohnya tabel mahasiswa. Kolom adalah attribute atau field dalam database, contohnya: Nama, NIM, Prodi. Sedangkan record adalah satu kumpulan nilai data, contohnya data milik satu mahasiswa
2. Fungsi primary key adalah identitas unik setiap record. Bersifat unik karena sebagai pembeda antara kolom satu dengan kolom yang lainnya. conyohnya id. 
3. Fungsi NOT NULL dalam konteks database adalah suatu record tidak boleh kosong, jadi setiap kolom harus terisi value. UNIQUE adalah suatu record yang memiliki nilai bersifat unik berfungsi sebagai identitas yang membedakan record satu dengan yang lainnya.   
4. Karena untuk menghilangkan kesalahan pahaman sistem dalam pembacaan data. cotohnya jika NIM memiliki angka nol di depan seperti 001361, maka yang terbaca oleh komputer hanya 1361. 

sesi 1 bagian 1.4 
1. Di mana file db dibuat, dan kenapa di sana? 
2. Apa bedanya connect() dan close()