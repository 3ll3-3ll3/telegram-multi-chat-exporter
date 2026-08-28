# Windows code signing and antivirus false positives

## Current state

The project currently publishes unsigned Windows binaries. Unsigned PyInstaller one-file executables can trigger reputation or heuristic warnings in antivirus products even when the source and build pipeline are clean.

An open-source license alone does **not** make antivirus products trust an executable. A self-signed certificate also does not provide normal public Windows publisher trust.

## Free open-source signing path: SignPath Foundation

This repository uses the MIT License and is intended to remain fully open source. That makes it eligible to apply for SignPath Foundation's free OSS code-signing program, subject to SignPath's review and acceptance.

Project maintainers should:

1. Apply at https://signpath.org/ for the open-source program.
2. Authorize the SignPath GitHub App for this repository when requested.
3. Create the SignPath project/artifact configuration for a Windows PE/EXE using Authenticode SHA-256.
4. Configure the approved signing policy.
5. Add the identifiers/tokens required by SignPath as GitHub repository secrets or variables according to SignPath's current GitHub integration documentation.
6. Update the release workflow so the artifact is signed **after build/tests and before the GitHub Release is created**.
7. Verify the signed output with `Get-AuthenticodeSignature` in CI.

Do not commit signing tokens, credentials or private keys to the repository.

## 360 false-positive handling

360 provides an official software false-positive submission form. For a clean release that is still detected:

1. Download the exact Release asset that users receive.
2. Verify its SHA-256 against the GitHub Release/build output.
3. Submit that EXE or ZIP and the detection screenshot to 360's software false-positive channel.
4. Include the public repository URL and Release URL so analysts can correlate the binary with its source.

For local development, 360's developer mode/trusted development directory can reduce interruptions, but this is only a local workaround and should not be treated as a distribution solution.

## Distribution formats

The project may publish both:

- **one-file EXE**: easiest to download, but implemented as a self-extracting executable;
- **portable onedir ZIP**: contains the application EXE plus runtime DLLs/files, avoids the one-file self-extraction layer and is useful when antivirus heuristics dislike the one-file build.

Signing is still recommended for either format.
