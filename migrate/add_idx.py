import pymongo

RB_LIST = [
    'rbRisarComplaints',
    'rbRisarCervix',
    'rbRisarCervical_Canal',
    'rbRisarVulvaSkin',
    'rbRisarUrethra',
    'rbRisarVaginaGenVisit',
    'rbRisarVaginaParies',
    'rbRisarVaginalFornix',
    'rbRisarOvary',
    'rbRisarParametrium1',
]


def add_idx():
    client = pymongo.MongoClient('127.0.0.1')
    db_nvesta = client['nvesta']
    refbooks = db_nvesta['refbooks']
    refbooks.update({
        "fields": {
            '$not': {
                '$elemMatch': {"key": "idx"}
            }
        },
        "code": {"$in": RB_LIST}
    }, {'$push': {"fields": {"mandatory" : False, "key" : "idx"} } }, multi=True)


if __name__ == '__main__':
    add_idx()
