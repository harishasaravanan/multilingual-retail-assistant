import asyncio
import unittest

from app.events import Broker, event_stream, sse_format


class EventTests(unittest.TestCase):
    def test_sse_format(self):
        self.assertEqual(sse_format("state", {"state": "listening"}),
                         'event: state\ndata: {"state": "listening"}\n\n')

    def test_native_script_is_not_escaped(self):
        self.assertIn("டவ்", sse_format("result", {"product": "டவ்"}))

    def test_stream_delivers_published_events_in_order(self):
        async def run():
            broker = Broker()
            stream = event_stream(broker, heartbeat=1)
            first = asyncio.ensure_future(stream.__anext__())
            await asyncio.sleep(0)          # let the stream subscribe
            broker.publish("state", {"state": "listening"})
            broker.publish("result", {"status": "OK"})
            a = await first
            b = await stream.__anext__()
            await stream.aclose()
            return a, b, len(broker._subs)
        a, b, subs = asyncio.run(run())
        self.assertTrue(a.startswith("event: state"))
        self.assertTrue(b.startswith("event: result"))
        self.assertEqual(subs, 0, "stream must unsubscribe when closed")

    def test_heartbeat_when_idle(self):
        async def run():
            stream = event_stream(Broker(), heartbeat=0.05)
            out = await stream.__anext__()
            await stream.aclose()
            return out
        self.assertEqual(asyncio.run(run()), ": keep-alive\n\n")

    def test_every_screen_gets_every_event(self):
        broker = Broker()
        q1, q2 = broker.subscribe(), broker.subscribe()
        broker.publish("state", {"state": "processing"})
        self.assertEqual(q1.get_nowait(), q2.get_nowait())


if __name__ == "__main__":
    unittest.main()
