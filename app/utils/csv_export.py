"""CSV 导出工具（P1）：生成带 BOM 的 UTF-8 CSV 响应，Excel 打开中文不乱码"""
import csv
import io

from fastapi import Response


def csv_response(filename: str, headers: list, rows: list) -> Response:
    buf = io.StringIO()
    buf.write('\ufeff')
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerows(rows)
    return Response(
        content=buf.getvalue(),
        media_type='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )
