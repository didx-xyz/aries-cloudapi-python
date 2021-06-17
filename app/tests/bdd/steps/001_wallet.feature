Feature: Provisioning DIDs and wallets
    A DID is created on the ledger

    Scenario: Getting a public DID
        Given I have an admin API key
        When I target the create DID endpoint
        Then I am able to generate a public DID