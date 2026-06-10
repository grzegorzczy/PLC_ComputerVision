# ============================================================
# fingerCounter.py
# Główny skrypt - liczy palce i wysyła wynik do OPC UA
# ============================================================

import cv2
import time
import os
from opcua import Client          # połączenie z Prosys OPC UA Server
import HandTrackingModule as ht   # nasz własny moduł detekcji dłoni


# ============================================================
# USTAWIENIA - zmień jeśli potrzeba
# ============================================================

OPC_UA_URL = "opc.tcp://DESKTOP-BUEJ0AV.mshome.net:53530/OPCUA/SimulationServer"
NODE_ID    = "ns=3;i=1008"   # ID zmiennej FingerCount którą stworzyliśmy w Prosys

CAMERA_ID  = 0               # 0 = domyślna kamera
IMG_FOLDER = "FingerImages"  # folder z obrazkami palców


# ============================================================
# KTÓRE PUNKTY PORÓWNUJEMY DLA KAŻDEGO PALCA
# Format: [czubek, staw_ponizej]
# ============================================================

# Dla palców 2-5: porównujemy Y (czubek wyżej = wyprostowany)
FINGER_TIPS = [8, 12, 16, 20]    # czubki: wskazujący, środkowy, serdeczny, mały
FINGER_MCP  = [6, 10, 14, 18]    # stawy poniżej czubków

# Kciuk osobno - porównujemy X (czubek bardziej w bok = wyprostowany)
THUMB_TIP = 4
THUMB_IP  = 3


# ============================================================
# POŁĄCZENIE Z OPC UA
# ============================================================

def connect_opc():
    """Łączy się z serwerem Prosys i zwraca węzeł FingerCount"""
    client = Client(OPC_UA_URL)
    client.connect()
    print("✅ Połączono z OPC UA Server")
    node = client.get_node(NODE_ID)
    return client, node


def send_value(node, value):
    """Wysyła liczbę palców do serwera OPC UA"""
    node.set_value(float(value))


# ============================================================
# ŁADOWANIE OBRAZKÓW (1.png, 2.png ... 6.png)
# ============================================================

def load_finger_images(folder):
    """
    Wczytuje obrazki z folderu FingerImages.
    Zakładamy że pliki nazywają się: 1.png, 2.png ... 6.png
    Zwraca listę obrazków [ img0, img1, img2, img3, img4, img5 ]
    indeks 0 = zero palców (5.png w oryginalnym projekcie to 0)
    """
    images = []
    for i in range(1, 7):    # 1, 2, 3, 4, 5, 6
        path = os.path.join(folder, f"{i}.png")
        img = cv2.imread(path)
        images.append(img)
    return images


# ============================================================
# LICZENIE PALCÓW
# ============================================================

def count_fingers(landmarks):
    """
    Na podstawie listy 21 punktów dłoni zlicza wyprostowane palce.
    Zwraca liczbę od 0 do 5.
    """
    if not landmarks:
        return 0

    fingers = []

    # --- KCIUK ---
    # Porównujemy X: jeśli czubek (4) jest bardziej w lewo niż staw (3)
    # to kciuk jest wyprostowany (dla prawej dłoni)
    if landmarks[THUMB_TIP][1] < landmarks[THUMB_IP][1]:
        fingers.append(1)   # wyprostowany
    else:
        fingers.append(0)   # zgięty

    # --- POZOSTAŁE 4 PALCE ---
    # Porównujemy Y: czubek wyżej (mniejsze Y) niż staw = wyprostowany
    for tip, mcp in zip(FINGER_TIPS, FINGER_MCP):
        if landmarks[tip][2] < landmarks[mcp][2]:
            fingers.append(1)   # wyprostowany
        else:
            fingers.append(0)   # zgięty

    # Sumujemy: [1, 1, 0, 0, 0] → 2 palce
    return sum(fingers)


# ============================================================
# GŁÓWNA PĘTLA
# ============================================================

def main():
    # Połącz z OPC UA
    try:
        opc_client, opc_node = connect_opc()
        opc_connected = True
    except Exception as e:
        print(f"⚠️  Brak połączenia OPC UA: {e}")
        print("   Program działa bez wysyłania danych.")
        opc_connected = False

    # Załaduj obrazki palców
    finger_images = load_finger_images(IMG_FOLDER)

    # Uruchom detektor dłoni
    detector = ht.HandDetector(max_hands=1, min_detection=0.75)

    # Otwórz kamerę
    cap = cv2.VideoCapture(CAMERA_ID)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    prev_time    = 0   # do obliczania FPS
    prev_fingers = -1  # poprzednia liczba palców (wysyłamy tylko gdy zmiana)

    print("🖐  Uruchomiono. Pokaż dłoń do kamery. ESC = wyjście.")

    while True:
        success, img = cap.read()
        if not success:
            print("❌ Błąd odczytu kamery")
            break

        # Wykryj dłoń i pobierz punkty
        img       = detector.find_hands(img)
        landmarks = detector.find_position(img)

        # Policz palce
        finger_count = count_fingers(landmarks)

        # Wyślij do OPC UA tylko gdy wartość się zmieniła
        if opc_connected and finger_count != prev_fingers:
            try:
                send_value(opc_node, finger_count)
                print(f"📤 Wysłano do OPC UA: {finger_count}")
            except Exception as e:
                print(f"⚠️  Błąd wysyłania: {e}")
        prev_fingers = finger_count

        # Wyświetl obrazek odpowiadający liczbie palców
        if finger_images[finger_count] is not None:
            img[0:200, 0:200] = cv2.resize(finger_images[finger_count], (200, 200))

        # Oblicz i wyświetl FPS
        curr_time = time.time()
        fps = int(1 / (curr_time - prev_time + 0.001))
        prev_time = curr_time
        cv2.putText(img, f"FPS: {fps}",          (10, 460),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        cv2.putText(img, f"Palce: {finger_count}", (10, 430),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)

        cv2.imshow("Finger Counter → OPC UA", img)

        if cv2.waitKey(1) == 27:   # ESC
            break

    # Sprzątamy po sobie
    cap.release()
    cv2.destroyAllWindows()
    if opc_connected:
        opc_client.disconnect()
        print("🔌 Rozłączono z OPC UA")


if __name__ == "__main__":
    main()