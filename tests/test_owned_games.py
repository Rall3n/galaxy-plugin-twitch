import pytest
from galaxy.api.consts import LicenseType
from galaxy.api.types import Game, LicenseInfo


def _api_owned_game(game_id, title):
    return {
        "product": {
            "id": game_id
            , "title": title
            , "productLine": "Twitch:FuelGame"
        }
    }


def _owned_game(game_id, game_title):
    return Game(game_id, game_title, None, LicenseInfo(LicenseType.SinglePurchase))


@pytest.fixture()
def get_local_games_mock(mocker):
    return mocker.patch("twitch_plugin.TwitchPlugin._get_local_games")


@pytest.mark.asyncio
@pytest.mark.parametrize("request_response, owned_games", [
    (Exception, [])
    , ([], [])
    , (
        [
            _api_owned_game("0c0126bf-8d56-46c0-ac10-fa07a4f2ad70", "The Banner Saga")
            , _api_owned_game("8530321b-a8dd-4a74-baa3-24a247454c36", "The Banner Saga 2")
            , _api_owned_game("f41d91c5-83b4-40e1-869e-01a0d6056f97", "Gone Home")
        ], [
            _owned_game("0c0126bf-8d56-46c0-ac10-fa07a4f2ad70", "The Banner Saga")
            , _owned_game("8530321b-a8dd-4a74-baa3-24a247454c36", "The Banner Saga 2")
            , _owned_game("f41d91c5-83b4-40e1-869e-01a0d6056f97", "Gone Home")
        ]
    )
])
async def test_owned_games(request_response, owned_games, installed_twitch_plugin, twitch_backend_client):
    twitch_backend_client.fetch_entitlements.return_value = request_response

    installed_twitch_plugin.handshake_complete()
    await installed_twitch_plugin._update_owned_games()

    assert owned_games == await installed_twitch_plugin.get_owned_games()

    twitch_backend_client.fetch_entitlements.assert_called_once()


_GAME_ID = "game-id"
_GAME_TITLE = "game title"


@pytest.mark.asyncio
@pytest.mark.parametrize("old_game_state, new_game_state, expected_calls", [
    # not owned -> not owned
    ([], [], [])
    # not owned -> owned
    , ([], [_api_owned_game(_GAME_ID, _GAME_TITLE)], ["add"])
    # owned -> owned
    , (
        [_api_owned_game(_GAME_ID, _GAME_TITLE)]
        , [_api_owned_game(_GAME_ID, _GAME_TITLE)]
        , []
    )
    # owned -> not owned
    , ([_api_owned_game(_GAME_ID, _GAME_TITLE)], [], ["remove"])
])
async def test_owned_game_update(
    old_game_state
    , new_game_state
    , expected_calls
    , installed_twitch_plugin
    , twitch_backend_client
    , get_local_games_mock
    , mocker
):
    # prepare
    twitch_backend_client.fetch_entitlements.return_value = old_game_state
    game_added_mock = mocker.patch("twitch_plugin.TwitchPlugin.add_game")
    game_removed_mock = mocker.patch("twitch_plugin.TwitchPlugin.remove_game")

    installed_twitch_plugin.handshake_complete()
    await installed_twitch_plugin.tick()
    assert twitch_backend_client.fetch_entitlements.call_count == 1

    # test
    twitch_backend_client.fetch_entitlements.return_value = new_game_state

    await installed_twitch_plugin.tick()
    assert twitch_backend_client.fetch_entitlements.call_count == 2

    if "add" in expected_calls:
        game_added_mock.assert_called_once_with(_owned_game(_GAME_ID, _GAME_TITLE))
    else:
        game_added_mock.assert_not_called()

    if "remove" in expected_calls:
        game_removed_mock.assert_called_once_with(_GAME_ID)
    else:
        game_removed_mock.assert_not_called()
