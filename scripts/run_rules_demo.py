from app.services.rules_engine import get_default_engine

def main():
    engine = get_default_engine()
    garments = [
        {"id": 10, "color": "白", "style": "休闲", "tags": ["夏季", "休闲"]},
        {"id": 11, "color": "蓝", "style": "正式", "tags": ["防水"]},
        {"id": 12, "color": "黑", "style": "休闲", "tags": ["冬季"]},
    ]

    print("Garments input:", garments)
    print("Candidates:")
    print(engine.recommend(garments, n=3))

if __name__ == '__main__':
    main()
