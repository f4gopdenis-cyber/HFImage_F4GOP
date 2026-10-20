"""Programme ouvert des jours : la mémoire du récepteur ne doit pas grossir sans fin."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import protocol as P  # noqa: E402


class Memoire(unittest.TestCase):
    def test_recepteur_borne(self):
        rx = P.Receiver()
        n = P.Receiver.KEEP + 30
        for i in range(n):
            data = os.urandom(3000)
            s = P.Sender(data, "jpeg", "F4GOP", 120, i)
            res = None
            for f in s.frames():
                res = rx.feed(f) or res
            self.assertIsNotNone(res, i)
            self.assertEqual(res[1], data)
            # image complète : plus de décodeur gardé, la progression reste lisible
            self.assertIsNone(rx.sessions[i]["dec"])
            got, K = rx.progress(i)
            self.assertEqual(got, K)
        self.assertEqual(rx.total, n)
        self.assertLessEqual(len(rx.done), P.Receiver.KEEP)
        self.assertLessEqual(len(rx.sessions), P.Receiver.KEEP)
        self.assertIn(n - 1, rx.done)                 # les plus récentes restent
        self.assertNotIn(0, rx.done)

    def test_trames_en_trop_apres_image_complete(self):
        """Des trames qui arrivent encore après la fin ne recréent pas de décodeur."""
        rx = P.Receiver()
        s = P.Sender(os.urandom(2000), "jpeg", "F4GOP", 120, 7)
        fr = s.frames(overhead=0.5)
        for f in fr:
            rx.feed(f)
        self.assertIsNone(rx.sessions[7]["dec"])
        for f in s.frames(extra=5):
            self.assertIsNone(rx.feed(f))
        self.assertIsNone(rx.sessions[7]["dec"])

    def test_images_envoyees_bornees(self):
        import types
        import app
        cls = next(c for c in vars(app).values() if isinstance(c, type) and hasattr(c, "_remember_sent"))
        fake = types.SimpleNamespace(sent_images={})
        for i in range(100):
            cls._remember_sent(fake, types.SimpleNamespace(image_id=i))
        self.assertEqual(len(fake.sent_images), 32)
        self.assertIn(99, fake.sent_images)


if __name__ == "__main__":
    unittest.main()
