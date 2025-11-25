#!/bin/bash
echo "---------------------------------------------"
echo "🎬 ANIL'IN SENARYO MASASI AÇILIYOR..."
echo "---------------------------------------------"

cd '/Volumes/MSI DATAMAG/YOUTUBE'

# Programı çalıştır
/Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11 -m streamlit run senarist.py

echo ""
echo "---------------------------------------------"
echo "❌ Program kapandı veya bir hata oluştu."
echo "Hata mesajını yukarıda görebilirsin."
read -p "Pencereyi kapatmak için ENTER tuşuna bas..."
