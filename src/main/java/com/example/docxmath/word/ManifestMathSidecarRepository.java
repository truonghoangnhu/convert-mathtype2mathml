package com.example.docxmath.word;

import com.example.docxmath.MathmlSidecarRegistry;

import java.io.IOException;
import java.nio.file.Path;

public final class ManifestMathSidecarRepository implements MathSidecarRepository {
    private final MathmlSidecarRegistry registry;

    private ManifestMathSidecarRepository(MathmlSidecarRegistry registry) {
        this.registry = registry;
    }

    public static ManifestMathSidecarRepository empty() {
        return new ManifestMathSidecarRepository(MathmlSidecarRegistry.empty());
    }

    public static ManifestMathSidecarRepository load(Path manifestFile) throws IOException {
        return new ManifestMathSidecarRepository(
                manifestFile == null ? MathmlSidecarRegistry.empty() : MathmlSidecarRegistry.load(manifestFile)
        );
    }

    @Override
    public String readMathml(String partName) throws IOException {
        return registry.readMathmlForPart(partName);
    }
}
