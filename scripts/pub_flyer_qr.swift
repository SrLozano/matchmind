#!/usr/bin/env swift

import CoreImage
import Foundation
import ImageIO
import UniformTypeIdentifiers

enum QRHelperError: Error, CustomStringConvertible {
    case usage
    case filterUnavailable
    case imageCreationFailed
    case imageWriteFailed
    case decodeFailed

    var description: String {
        switch self {
        case .usage:
            return "Usage: pub_flyer_qr.swift encode <url> <output.png> | decode <input.png>"
        case .filterUnavailable:
            return "Core Image QR filter is unavailable."
        case .imageCreationFailed:
            return "Unable to create QR image."
        case .imageWriteFailed:
            return "Unable to write QR PNG."
        case .decodeFailed:
            return "Unable to decode a QR code from the image."
        }
    }
}

func encode(message: String, outputPath: String) throws {
    guard let filter = CIFilter(name: "CIQRCodeGenerator") else {
        throw QRHelperError.filterUnavailable
    }

    filter.setValue(Data(message.utf8), forKey: "inputMessage")
    filter.setValue("Q", forKey: "inputCorrectionLevel")

    guard let outputImage = filter.outputImage else {
        throw QRHelperError.imageCreationFailed
    }

    let scaledImage = outputImage.transformed(by: CGAffineTransform(scaleX: 12, y: 12))
    let context = CIContext(options: [.useSoftwareRenderer: true])
    guard let cgImage = context.createCGImage(scaledImage, from: scaledImage.extent) else {
        throw QRHelperError.imageCreationFailed
    }

    let outputURL = URL(fileURLWithPath: outputPath)
    guard let destination = CGImageDestinationCreateWithURL(
        outputURL as CFURL,
        UTType.png.identifier as CFString,
        1,
        nil
    ) else {
        throw QRHelperError.imageWriteFailed
    }

    CGImageDestinationAddImage(destination, cgImage, nil)
    guard CGImageDestinationFinalize(destination) else {
        throw QRHelperError.imageWriteFailed
    }
}

func decode(inputPath: String) throws -> String {
    let inputURL = URL(fileURLWithPath: inputPath)
    guard let inputImage = CIImage(contentsOf: inputURL) else {
        throw QRHelperError.imageCreationFailed
    }

    let options = [CIDetectorAccuracy: CIDetectorAccuracyHigh]
    guard let detector = CIDetector(
        ofType: CIDetectorTypeQRCode,
        context: CIContext(options: [.useSoftwareRenderer: true]),
        options: options
    ) else {
        throw QRHelperError.decodeFailed
    }

    for feature in detector.features(in: inputImage) {
        if let qrFeature = feature as? CIQRCodeFeature, let value = qrFeature.messageString {
            return value
        }
    }

    throw QRHelperError.decodeFailed
}

do {
    let arguments = CommandLine.arguments
    guard arguments.count >= 3 else {
        throw QRHelperError.usage
    }

    switch arguments[1] {
    case "encode":
        guard arguments.count == 4 else {
            throw QRHelperError.usage
        }
        try encode(message: arguments[2], outputPath: arguments[3])
    case "decode":
        guard arguments.count == 3 else {
            throw QRHelperError.usage
        }
        print(try decode(inputPath: arguments[2]))
    default:
        throw QRHelperError.usage
    }
} catch {
    fputs("error: \(error)\n", stderr)
    exit(1)
}
