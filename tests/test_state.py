import os
import tempfile
from proxcloud.state import State


def test_state_set_get():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    s = State(path)
    assert s.get("x") is None
    s.set("x", "1.2.3.4", "meta")
    assert s.get("x") == "1.2.3.4"
    s.set("x", "5.6.7.8")
    assert s.get("x") == "5.6.7.8"
    s.close()
    os.remove(path)
