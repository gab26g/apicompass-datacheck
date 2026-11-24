# Third-party software and original contribution

APICompass uses the LibreChat interface and runtime, release v0.8.8, from https://github.com/LibreChat-AI/LibreChat. The local Compose file pins the Linux amd64 image manifest at ghcr.io/librechat-ai/librechat@sha256:1e3bd3ac2cdbbcd64bdc4ef04c850d6fef5392d1fcb22cea46c5dcba17da7b95. The notice below was checked against /app/LICENSE in that running image. The upstream source snapshot in upstream/ is ignored; the pinned image and configuration reproduce the current integration.

Original project work includes the DataCheck API, invented fixtures and contracts, expected findings, API/validation/storage/privacy tests, bounded tool integration, agent instructions and project configuration. LibreChat itself was not written by the student. Python, FastAPI, Uvicorn, Boto3/Botocore and MongoDB remain their respective authors' software. MongoDB is separately licensed; deployment of its official image is not a claim that all stack components are MIT-licensed. Preserve applicable notices when distributing third-party source or binaries.

The final submission still needs the student's contribution record and AI-assistance declaration. Do not treat this notice as a signed declaration or assume an upstream source snapshot has been packaged in the submission ZIP.

## LibreChat MIT notice

MIT License

Copyright (c) 2026 LibreChat

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
