from pathlib import Path
from unittest.mock import patch

from iaa.tasks import R
from iaa.tasks.globals import handle_network_error


def test_network_error_resource():
    with patch('iaa.tasks.globals.server', return_value='en'), patch.object(R, 'NetworkError', object()):
        assert handle_network_error() is False

    token = R.current_variant.set('cn')
    try:
        prefabs = (
            R.NetworkError.DialogConnectionError.Text,
            R.NetworkError.DialogConnectionError.ButtonRetry,
            R.NetworkError.DialogReturningToTitle.Text,
            R.NetworkError.DialogReturningToTitle.ButtonOk,
        )
        assert all(Path(prefab.template.file_path).is_file() for prefab in prefabs)
        with (
            patch('iaa.tasks.globals.server', return_value='cn'),
            patch.object(R.NetworkError.DialogConnectionError.Text, 'exists', return_value=True),
            patch.object(R.NetworkError.DialogConnectionError.ButtonRetry, 'click', return_value=True),
        ):
            assert handle_network_error() is True
    finally:
        R.current_variant.reset(token)


if __name__ == '__main__':
    test_network_error_resource()
