SEAT_CHECK_ENDPOINT = "https://api-yebsp.tcddtasimacilik.gov.tr/koltuk/klCheck"
STATION_LIST_ENDPOINT = (
    "https://api-yebsp.tcddtasimacilik.gov.tr/istasyon/istasyonYukle"
)
SELECT_EMPTY_SEAT_ENDPOINT = "https://api-yebsp.tcddtasimacilik.gov.tr/koltuk/klSec"
RELEASE_SEAT_ENDPOINT = "https://api-yebsp.tcddtasimacilik.gov.tr/koltuk/klBirak"
TRIP_SEARCH_ENDPOINT = "https://api-yebsp.tcddtasimacilik.gov.tr/sefer/seferSorgula"
VAGON_SEARCH_ENDPOINT = (
    "https://api-yebsp.tcddtasimacilik.gov.tr/vagon/vagonBosYerSorgula"
)
VAGON_HARITA_ENDPOINT = (
    "https://api-yebsp.tcddtasimacilik.gov.tr/vagon/vagonHaritasindanYerSecimi"
)
VB_ENROLL_CONTROL_ENDPOINT = (
    "https://api-yebsp.tcddtasimacilik.gov.tr/odeme/vbEnrollControl"
)
PRICE_ENDPOINT = (
    "https://api-yebsp.tcddtasimacilik.gov.tr/fiyatlandirma/anahatFiyatSimple"
)
VB_ODEME_SORGU = "https://api-yebsp.tcddtasimacilik.gov.tr/odeme/vbOdemeSorgu"
TICKET_RESERVATION_ENDPOINT = (
    "https://api-yebsp.tcddtasimacilik.gov.tr/bilet/biletSatisRezervasyon"
)
MERNIS_DOGRULAMA_ENDPOINT = (
    "https://api-yebsp.tcddtasimacilik.gov.tr/yebsp/tcNoMernisDogrula"
)

DISABLED_SEAT_IDS = [
    13485128303,
    13029825502,
    13485128302,
    13371669503,
    15196333600,
    27948604352,
]
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
    "Sec-Fetch-Site": "cross-site",
}

STATION_LIST_REQUEST_BODY = (
    '{"kanalKodu":"3","dil":1,"tarih":"Nov 10, 2011 12:00:00 AM","satisSorgu":true}'
)

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
    "inisIstId": None,
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
    "dakika": 1,
    "huawei": False,
}

trip_search_req_body = {
    "kanalKodu": 3,
    "dil": 0,
    "seferSorgulamaKriterWSDVO": {
        "satisKanali": 3,
        "binisIstasyonu": None,
        "binisIstasyonu_isHaritaGosterimi": "false",
        "inisIstasyonu": None,
        "inisIstasyonu_isHaritaGosterimi": "false",
        "seyahatTuru": 1,
        "gidisTarih": None,  # "Dec 10, 2023 12:10:00 PM"
        "bolgeselGelsin": "false",
        "islemTipi": 0,
        "yolcuSayisi": 1,
        "aktarmalarGelsin": "true",
        "binisIstasyonId": None,
        "inisIstasyonId": None,
    },
}


price_req_body = {
    "anahatFiyatHesKriterWSDVO": {"islemTipi": 0, "seyahatSorgulamaTuru": 1},
    "yolcuList": [
        {
            "siraNo": 1,
            "cinsiyet": "E",
            "tarifeId": None,  # 11750067704: TSK calisan , 1: tam(adult)
            "seferKoltuk": [
                {
                    "seferBaslikId": None,
                    "aktarmaSiraNo": "0",
                    "binisIstasyonId": None,
                    "inisIstasyonId": None,
                    "biletTipi": 1,
                    "gidisMi": True,
                    "binisTarihi": None,  # "Dec 10, 2023 12:10:00 PM"
                    "vagonSiraNo": None,
                    "vagonTipi": None,  # 0 economy, 1 business
                    "koltukNo": None,
                }
            ],
        }
    ],
    "kanalKodu": "3",
    "dil": 0,
}

vb_enroll_control_req_body = {
    "kanalKodu": 3,
    "dil": 0,
    "islemTipi": 0,
    "yebspPaymentSuccessUrl": "https://bilet.tcdd.gov.tr/odeme-sonuc",
    "yebspPaymentFailureUrl": "https://bilet.tcdd.gov.tr/odeme",
    "biletRezOdemeBilgileri": {
        "krediKartNO": None,
        "krediKartSahibiAdSoyad": None,
        "ccv": None,
        "sonKullanmaTarihi": None,
        "toplamBiletTutari": None,
        "krediKartiTutari": None,
        "abonmanTutar": 0,
        "acikBiletKuponNoList": [],
        "acikBiletTutar": 0,
        "islemYeri": "7",
        "milPuan": 0,
    },
    "koltukLockList": [],
}

ticket_reservation_req_body = {
    "kanalKodu": "3",
    "dil": 0,
    "islemTipi": 0,
    "biletRezYerBilgileri": [
        {
            "biletWSDVO": {
                "seferBaslikId": None,
                "aktarmaSiraNo": "0",
                "binisIstasyonId": None,
                "inisIstasyonId": None,
                "hareketTarihi": None,
                "varisTarihi": None,
                "biletTipi": 1,
                "maliyeNo": 0,
                "grupMu": False,
                "cezali": False,
                "farkBileti": False,
                "bagajBileti": False,
                "hesCode": "",
                "yolcuSiraNo": 1,
                "tarifeId": None,
                "tckn": None,
                "ad": None,
                "soyad": None,
                "dogumTar": None,
                "iletisimEposta": None,
                "iletisimCepTel": None,
                "cinsiyet": None,
                "vagonSiraNo": None,
                "koltukNo": None,
                "ucret": None,
                "statu": 0,
                # this looks like 2 for gidis, dunno what it is for gidis-donus
                "seyahatTur": 2,
                "trenTurTktId": 49549,
                # This changes the price even for bussiness class even though it should not
                "vagonTipi": 0,
                "koltukBazUcret": None,  # may not be necessary
                "indirimsizUcret": None,  # may not be necessary
                "minimumTasimaUcretiFarki": 0,
            }
        }
    ],
    "biletRezOdemeBilgileri": {
        "vposReference": None,
        "krediKartSahibiAdSoyad": None,
        "krediKartNO": None,
        "toplamBiletTutari": None,
        "krediKartiTutari": None,
        "abonmanTutar": 0,
        "acikBiletTutar": 0,
        "islemYeri": "7",
        "milPuan": 0,
        "permiDetayList": [],
    },
    "koltukLockIdList": [],
}

# vb_enroll_control_req_body = {
#     "kanalKodu": 3,
#     "dil": 0,
#     "islemTipi": 0,
#     "yebspPaymentSuccessUrl": "https://bilet.tcdd.gov.tr/odeme-sonuc",
#     "yebspPaymentFailureUrl": "https://bilet.tcdd.gov.tr/odeme",
#     "biletRezOdemeBilgileri": {
#         "krediKartNO": "6501700157813193",
#         "krediKartSahibiAdSoyad": "izzet can karakuş",
#         "ccv": "360",
#         "sonKullanmaTarihi": 3004,
#         "toplamBiletTutari": None,  # 370
#         "krediKartiTutari": None,  # 370
#         "abonmanTutar": 0,
#         "acikBiletKuponNoList": [],
#         "acikBiletTutar": 0,
#         "islemYeri": "7",
#         "milPuan": 0
#     },
#     "koltukLockList": []
# }

ticket_reservation_req_body = {
    "kanalKodu": "3",
    "dil": 0,
    "islemTipi": 0,
    "biletRezYerBilgileri": [
        {
            "biletWSDVO": {
                "seferBaslikId": None,
                "aktarmaSiraNo": "0",
                "binisIstasyonId": None,
                "inisIstasyonId": None,
                "hareketTarihi": None,
                "varisTarihi": None,
                "biletTipi": 1,
                "maliyeNo": 0,
                "grupMu": False,
                "cezali": False,
                "farkBileti": False,
                "bagajBileti": False,
                "hesCode": "",
                "yolcuSiraNo": 1,
                "tarifeId": None,
                "vagonSiraNo": None,
                "koltukNo": None,
                "ucret": None,
                "tckn": None,
                "ad": None,
                "soyad": None,
                "dogumTar": None,
                "iletisimEposta": None,
                "iletisimCepTel": None,
                "cinsiyet": None,
                "trenTurTktId": None,
                "koltukBazUcret": None,
                "indirimsizUcret": None,
                "statu": 0,
                "seyahatTur": 2,
                "vagonTipi": 0,
                "minimumTasimaUcretiFarki": 0,
            }
        }
    ],
    "biletRezOdemeBilgileri": {
        "vposReference": "snkzt4ttvw2gmuxyrwa4vfbjkwzvtiqmz4mpwn3n",
        "krediKartSahibiAdSoyad": "izzet can karakus",
        "krediKartNO": "4506347008156065",
        "toplamBiletTutari": 370,
        "krediKartiTutari": 370,
        "abonmanTutar": 0,
        "acikBiletTutar": 0,
        "islemYeri": "7",
        "milPuan": 0,
        "permiDetayList": [],
    },
    "koltukLockIdList": [
        43502967424,
        43502967425,
        43502967426,
        43502967427,
        43502967428,
        43502967429,
        43502967430,
        43502967431,
        43502967432,
    ],
}


mernis_dogrula_req_body = {
    "kanalKodu": "3",
    "dil": 1,
    "ad": None,
    "soyad": None,
    "dogumTar": "Jul 14, 1994 00:00:00 AM",
    "tckn": None,
}
