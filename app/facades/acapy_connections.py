from typing import List

from aries_cloudcontroller import AcaPyClient, ConnRecord


async def get_connections_by_invitation_key(
    aries_controller: AcaPyClient, invitation_key: str
) -> List[ConnRecord]:
    # Make sure the issuer has a connection with the endorser
    connections = await aries_controller.connection.get_connections(
        invitation_key=invitation_key
    )

    # FIXME: invitation key is not taken into account for filter
    # will be fixed in ACA-Py 0.7.3
    # https://github.com/hyperledger/aries-cloudagent-python/pull/1570
    connections = [
        result
        for result in (connections.results or [])
        if result.invitation_key == invitation_key
    ]

    return connections
