from __future__ import annotations

import numpy as np
import cv2
from PIL import Image

from core_processor.settings import OCR_MAX_DIM, OCR_MIN_DIM


def _order_points(pts: np.ndarray) -> np.ndarray:
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def _four_point_transform(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
    rect = _order_points(pts)
    tl, tr, br, bl = rect
    width = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
    height = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
    dst = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], dtype="float32")
    m = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, m, (width, height))


def _crop_document(img: Image.Image) -> Image.Image:
    orig = np.array(img.convert("RGB"))
    gray = cv2.cvtColor(orig, cv2.COLOR_RGB2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    otsu_thresh, _ = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    edges = cv2.Canny(blurred, otsu_thresh * 0.5, otsu_thresh)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    img_area = orig.shape[0] * orig.shape[1]
    doc_contour = None
    for c in contours[:10]:
        area = cv2.contourArea(c)
        if area < 0.15 * img_area or area > 0.98 * img_area:
            continue
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            doc_contour = approx.reshape(4, 2).astype("float32")
            break
    if doc_contour is None:
        return img
    return Image.fromarray(_four_point_transform(orig, doc_contour))


def _resize_for_ocr(img: Image.Image) -> Image.Image:
    w, h = img.size
    long_side = max(w, h)
    if long_side <= OCR_MAX_DIM:
        return img
    scale = OCR_MAX_DIM / long_side
    new_w, new_h = int(w * scale), int(h * scale)
    if min(new_w, new_h) < OCR_MIN_DIM:
        scale = OCR_MIN_DIM / min(w, h)
        new_w, new_h = int(w * scale), int(h * scale)
    return img.resize((new_w, new_h), Image.LANCZOS)
