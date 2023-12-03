SEAT_CHECK_ENDPOINT = "https://api-yebsp.tcddtasimacilik.gov.tr/koltuk/klCheck"
SELECT_EMPTY_SEAT_ENDPOINT = "https://api-yebsp.tcddtasimacilik.gov.tr/koltuk/klSec"
TRIP_SEARCH_ENDPOINT = "https://api-yebsp.tcddtasimacilik.gov.tr/sefer/seferSorgula"
VAGON_SEARCH_ENDPOINT = "https://api-yebsp.tcddtasimacilik.gov.tr/vagon/vagonBosYerSorgula"
VAGON_HARITA_ENDPOINT = "https://api-yebsp.tcddtasimacilik.gov.tr/vagon/vagonHaritasindanYerSecimi"
VB_ENROLL_CONTROL_ENDPOINT = "https://api-yebsp.tcddtasimacilik.gov.tr/odeme/vbEnrollControl"
PRICE_ENDPOINT = "https://api-yebsp.tcddtasimacilik.gov.tr/fiyatlandirma/anahatFiyatSimple"

SEATS_IDS = [13371893752, 13371893753, 16801693056, 16801693057]
TARIFFS = { 'TSK': 11750067704, 'TAM': 1 }
REQUEST_HEADER = {
    "Host": "api-yebsp.tcddtasimacilik.gov.tr",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Accept": "*/*",
    "Accept-Language": "en-US,tr-TR;q=0.8,tr;q=0.5,en;q=0.3",
    "Accept-Encoding": "gzip, deflate, br",
    "Authorization": "Basic ZGl0cmF2b3llYnNwOmRpdHJhMzQhdm8u",
    "Content-Type": "application/json",
    "Origin": "https://bilet.tcdd.gov.tr",
    "Connection": "keep-alive",
    "Referer": "https://bilet.tcdd.gov.tr/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "cross-site"
}

vagon_harita_req_body = {
    "kanalKodu": "3",
    "dil": 0,
    "seferBaslikId": None,
    "vagonSiraNo": None,
    "binisIst": None,
    "InisIst": None,
}

vagon_req_body = {
    "kanalKodu": "3",
    "dil": 0,
    "seferBaslikId": None,
    "binisIstId": None,
    "inisIstId": None
}


seat_check = {
    "kanalKodu": "3",
    "dil": 0,
    "seferId": None,
    "seciliVagonSiraNo": None,
    "koltukNo": None,
}
koltuk_sec_req_body = {
    "kanalKodu": "3",
    "dil": 0,
    "seferId": None,
    "vagonSiraNo": None,
    "koltukNo": None,
    "cinsiyet": "E",
    "binisIst": None,
    "inisIst": None,
    "dakika": 10,
    "huawei": False
}

trip_search_req_body = {
    "kanalKodu": 3,
    "dil": 0,
    "seferSorgulamaKriterWSDVO": {
        "satisKanali": 3,
        "binisIstasyonu": None,
        "binisIstasyonu_isHaritaGosterimi": 'false',
        "inisIstasyonu": None,
        "inisIstasyonu_isHaritaGosterimi": 'false',
        "seyahatTuru": 1,
        "gidisTarih": "Nov 30, 2023 00:00:00 AM",
        "bolgeselGelsin": 'false',
        "islemTipi": 0,
        "yolcuSayisi": 1,
        "aktarmalarGelsin": 'true',
        "binisIstasyonId": None,
        "inisIstasyonId": None
    }
}

price_req_body = {
    "anahatFiyatHesKriterWSDVO": {
        "islemTipi": 0,
        "seyahatSorgulamaTuru": 1
    },
    "yolcuList": [
        {
            "siraNo": 1,
            "cinsiyet": "E",
            "tarifeId": None, # 11750067704: TSK calisan , 1: tam(adult)
            "seferKoltuk": [
                {
                    "seferBaslikId": None,
                    "aktarmaSiraNo": "0",
                    "binisIstasyonId": None,
                    "inisIstasyonId": None,
                    "biletTipi": 1,
                    "gidisMi": True,
                    "binisTarihi": "Dec 10, 2023 12:10:00 PM",
                    "vagonSiraNo": None,
                    "vagonTipi": None, # 0 economy, 1 business
                    "koltukNo": None
                }
            ]
        }
    ],
    "kanalKodu": "3",
    "dil": 0
}

vb_enroll_control_req_body = {
    "kanalKodu": 3,
    "dil": 0,
    "islemTipi": 0,
    "yebspPaymentSuccessUrl": "https://bilet.tcdd.gov.tr/odeme-sonuc",
    "yebspPaymentFailureUrl": "https://bilet.tcdd.gov.tr/odeme",
    "biletRezOdemeBilgileri": {
        "krediKartNO": "4506347008156065",
        "krediKartSahibiAdSoyad": "izzet can karakuş",
        "ccv": "035",
        "sonKullanmaTarihi": 2406,
        "toplamBiletTutari": 370,
        "krediKartiTutari": 370,
        "abonmanTutar": 0,
        "acikBiletKuponNoList": [],
        "acikBiletTutar": 0,
        "islemYeri": "7",
        "milPuan": 0
    },
    "koltukLockList": []
}
