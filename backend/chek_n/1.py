
import json
from django.http import HttpResponse

def webhook(request):
    if request.method == "POST":
        # Логируем в консоль Django (ты увидишь это в терминале с runserver)
        print("--- Пришёл вебхук от MAX ---")
        print("Headers:", dict(request.headers))
        print("Body:", request.body.decode('utf-8', errors='ignore'))
        
        # Проверка секрета (опционально, но полезно)
        secret = request.headers.get('X-Max-Bot-Api-Secret')
        if secret != 'my_secret_123':
            print("⚠️ Секретный ключ не совпадает!")
        else:
            print("✅ Секретный ключ верный.")
        
        return HttpResponse(status=200)
    return HttpResponse(status=405)