from app import app

try:
    with app.test_client() as c:
        res = c.get('/bunnies')
        print('STATUS', res.status_code)
        print(res.get_data(as_text=True)[:2000])
except Exception as e:
    import traceback
    traceback.print_exc()
    print('\nException:', e)
