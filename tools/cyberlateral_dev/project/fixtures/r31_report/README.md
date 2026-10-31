# R32 data-only fixtures

The four portable files for each profile are exact preserved bytes from R31's
two explicitly constructed repository examples, not real logs or an independent
numerical oracle. Source snapshot1d74f9dbcaa2a0bcde1a97afa5e97c09068881da,
publication101856a9a17b891d73308f65edf7e1186bea4c76. Sealed R31 ZIP SHA256
392947e4b0c918237b1a2da776fdba3115863e3193c51d70c358e59603510fc8.

sign RESULTS SHA190df9c03c38be9148117a6cbb40a4094380501a8be7d07d42e76eb6e26db06f,
resumed RESULTS SHAc3cf6fe3ed402b0a70b8c3f8f0fd33d078eb09bd90306ad5f3dd3c759c83ae4a.
Actual environment receipts are intentionally not committed. The test helper
constructs a complete clearly declared receipt and recomputes the five-entry
manifest in temporary directories only. No fixture generation calls the model.
