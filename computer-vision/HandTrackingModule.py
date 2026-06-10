# ============================================================
# HandTrackingModule.py
# Moduł do wykrywania dłoni za pomocą biblioteki MediaPipe.
# Używamy go jako "narzędzia" importowanego przez fingerCounter.py
# ============================================================

import cv2          # OpenCV - obsługa kamery i rysowanie na obrazie
import mediapipe as mp  # MediaPipe - silnik AI do wykrywania dłoni


class HandDetector:
    """
    Klasa wykrywająca dłonie na obrazie z kamery.
    MediaPipe zwraca 21 punktów (landmarks) na każdej dłoni.
    """

    def __init__(self, mode=False, max_hands=1, min_detection=0.75, min_tracking=0.5):
        """
        Konstruktor - ustawia parametry detektora.

        mode          : False = tryb wideo (szybszy), True = pojedyncze zdjęcia
        max_hands     : ile dłoni jednocześnie wykrywamy (1 wystarczy)
        min_detection : pewność wykrycia dłoni (0.0 - 1.0), im wyżej tym dokładniej
        min_tracking  : pewność śledzenia dłoni między klatkami
        """
        self.mode = mode
        self.max_hands = max_hands
        self.min_detection = min_detection
        self.min_tracking = min_tracking

        # Inicjalizacja modułu dłoni z MediaPipe
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=self.mode,
            max_num_hands=self.max_hands,
            min_detection_confidence=self.min_detection,
            min_tracking_confidence=self.min_tracking
        )

        # Narzędzie do rysowania szkieletu dłoni na obrazie
        self.mp_draw = mp.solutions.drawing_utils

        # Wyniki detekcji - będą tu przechowywane po każdym wywołaniu find_hands()
        self.results = None

    def find_hands(self, img, draw=True):
        """
        Wykrywa dłonie na obrazie i opcjonalnie rysuje szkielet.

        img  : obraz z kamery (BGR)
        draw : czy rysować punkty i połączenia dłoni na obrazie

        Zwraca obraz (z narysowaną dłonią lub nie).
        """
        # MediaPipe wymaga obrazu w formacie RGB (kamera daje BGR)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Przetwarzamy obraz - AI szuka dłoni
        self.results = self.hands.process(img_rgb)

        # Jeśli znaleziono przynajmniej jedną dłoń
        if self.results.multi_hand_landmarks:
            for hand_landmarks in self.results.multi_hand_landmarks:
                if draw:
                    # Rysujemy 21 punktów i połączenia między nimi
                    self.mp_draw.draw_landmarks(
                        img,
                        hand_landmarks,
                        self.mp_hands.HAND_CONNECTIONS
                    )

        return img

    def find_position(self, img, hand_index=0, draw=False):
        """
        Zwraca listę współrzędnych wszystkich 21 punktów dłoni.

        img        : obraz z kamery
        hand_index : który numer dłoni (0 = pierwsza znaleziona)
        draw       : czy rysować kółka na każdym punkcie

        Zwraca listę: [ [id, x, y], [id, x, y], ... ] dla 21 punktów
        Zwraca pustą listę [] jeśli nie wykryto dłoni.
        """
        landmark_list = []

        if self.results and self.results.multi_hand_landmarks:
            # Pobieramy punkty wybranej dłoni
            my_hand = self.results.multi_hand_landmarks[hand_index]

            height, width, _ = img.shape  # rozmiar obrazu w pikselach

            for point_id, landmark in enumerate(my_hand.landmark):
                # landmark.x i landmark.y są w zakresie 0.0 - 1.0 (procenty)
                # Przeliczamy na piksele
                cx = int(landmark.x * width)
                cy = int(landmark.y * height)

                landmark_list.append([point_id, cx, cy])

                if draw:
                    cv2.circle(img, (cx, cy), 8, (255, 0, 255), cv2.FILLED)

        return landmark_list


# ============================================================
# TEST - uruchamiany tylko gdy odpalimy ten plik bezpośrednio
# (nie wykonuje się przy imporcie w fingerCounter.py)
# ============================================================
if __name__ == "__main__":
    cap = cv2.VideoCapture(0)  # otwórz kamerę (0 = domyślna)
    detector = HandDetector()

    while True:
        success, img = cap.read()
        if not success:
            break

        img = detector.find_hands(img)
        landmarks = detector.find_position(img)

        if landmarks:
            # Wyświetl współrzędne czubka palca wskazującego (punkt nr 8)
            print(f"Czubek wskazującego: {landmarks[8]}")

        cv2.imshow("Test HandTrackingModule", img)

        if cv2.waitKey(1) == 27:  # ESC = wyjście
            break

    cap.release()
    cv2.destroyAllWindows()