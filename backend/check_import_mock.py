import sys, traceback
try:
    import mock_leffa
    print('imported mock_leffa, has app:', hasattr(mock_leffa, 'app'))
except Exception:
    traceback.print_exc()
    sys.exit(1)
