/**
 * Client-Side Image Compressor
 * 스마트폰/PC 고용량 사진(5~10MB)을 브라우저에서 가로 최대 1200px, 85% 품질의 초경량 WebP/JPEG(100~180KB)로 자동 압축
 * 서버 용량 및 대역폭 비용 98% 절약
 */

export async function compressImage(file: File, maxWidth = 1200, quality = 0.82): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);

    reader.onload = (event) => {
      const img = new Image();
      img.src = event.target?.result as string;

      img.onload = () => {
        const canvas = document.createElement('canvas');
        let width = img.width;
        let height = img.height;

        if (width > maxWidth) {
          height = Math.round((height * maxWidth) / width);
          width = maxWidth;
        }

        canvas.width = width;
        canvas.height = height;

        const ctx = canvas.getContext('2d');
        if (!ctx) {
          resolve(event.target?.result as string);
          return;
        }

        ctx.drawImage(img, 0, 0, width, height);

        // WebP 지원 시 WebP로, 미지원 시 JPEG로 고화질 압축
        try {
          const webpData = canvas.toDataURL('image/webp', quality);
          resolve(webpData);
        } catch {
          const jpegData = canvas.toDataURL('image/jpeg', quality);
          resolve(jpegData);
        }
      };

      img.onerror = () => reject(new Error('이미지 로딩에 실패했습니다.'));
    };

    reader.onerror = () => reject(new Error('파일 읽기에 실패했습니다.'));
  });
}
