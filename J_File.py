# -*- coding: utf-8 -*-
import os
import traceback
import shutil
import ezdxf
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon
import pandas as pd
import re
import datetime
import time  # <--- 이 줄이 누락되어 오류가 발생했습니다
import sys
import urllib.request
import email.utils
import fiona
import shapely
import shapely.ops
from shapely.geometry import shape
import glob
import pyproj

import init_proj  # 다른 지리 라이브러리보다 먼저 임포트
import J_security
import J_Field
import J_Error


from pathlib import Path  # <--- 이 부분이 빠지면 'Path' is not defined 에러가 납니다!
from tkinter import messagebox
from collections import defaultdict




if 'CONDA_PREFIX' in os.environ:
    try:
        proj_path = os.path.join(os.environ['CONDA_PREFIX'], "Library", "share", "proj") # 경로 변수 추가
        pyproj.datadir.set_data_dir(proj_path)
    except Exception:
        pass



sys.excepthook = J_Error.global_error_handler

def Remove_File(file_path):
    """
    [#파일 #삭제 #제거 #안전]
    파일 삭제) 지정된 경로의 파일을 시스템에서 영구적으로 제거합니다.

    입력 항목:
        file_path (str): 삭제할 파일의 전체 경로 (예: "C:/Data/temp.gpkg").

    반환값:
        bool: 삭제 성공 시 True, 파일이 존재하지 않거나 권한 문제로 실패 시 False.

    사용 예제:
        # 작업이 완료된 중간 가공 파일을 삭제하여 용량 확보
        J_File.Remove_File("D:/Project/Result/Temp_Step1.gpkg")

    주의 사항:
        - [영구 삭제]: 휴지통을 거치지 않고 즉시 삭제되므로 중요 데이터 삭제 시 주의가 필요합니다.
        - [권한 확인]: 삭제하려는 파일이 Global Mapper나 QGIS 등 다른 프로그램에서 열려 있을 경우 PermissionError가 발생할 수 있습니다.
        - [경로 출력]: [2026-01-27] 지침에 따라 출력창의 경로 가독성을 위해 모든 백슬래시(\)는 이중화(\\)하여 표시합니다.
    """
    try:
        # 1. 파일 존재 여부 확인
        if not os.path.exists(file_path):
            # [2026-01-27] 백슬래시 이중화 처리
            print(f"⚠️ 파일을 찾을 수 없습니다: {file_path.replace('\\', '\\\\')}")
            return False

        # 2. 파일 삭제 실행
        os.remove(file_path)
        print(f"🗑️ 파일 삭제 완료: {os.path.basename(file_path)}")
        return True

    except PermissionError:
        print(f"❌ 권한 오류: 파일이 다른 프로그램에서 사용 중입니다. ({os.path.basename(file_path)})")
        return False
    except Exception as e:
        print(f"🔥 파일 삭제 중 오류 발생: {str(e).replace('\\', '\\\\')}")
        return False

def NewFolder(parent_dir, folder_name, mode="REPLACE"):
    """
    [#폴더 #디렉토리 #생성]
    디렉토리) 지정된 위치에 새로운 폴더를 생성하고 경로를 반환합니다.

    입력 항목:
        parent_dir (str): 부모 디렉토리 경로.
        folder_name (str): 생성할 폴더명.
        mode (str): 'REPLACE' (기본값, 기존 폴더 삭제 후 재생성) 또는 'KEEP' (기존 폴더 유지).

    반환값:
        str: 생성된 폴더의 절대 경로 (실패 시 None).

    사용 예제:
        J_File.NewFolder("C:/Project", "01_Temp", mode="REPLACE")

    주의 사항:
        - REPLACE 모드 사용 시 기존 폴더 내의 모든 데이터가 삭제되므로 주의가 필요합니다.
        - os.path.abspath를 사용하여 항상 절대 경로를 반환합니다.
    """
    # 1. 경로 병합 및 절대 경로 변환 (경로 오류 방지)
    target_path = os.path.abspath(os.path.join(parent_dir, folder_name))

    try:
        if os.path.exists(target_path):
            if mode.upper() == "REPLACE":
                # 기존 폴더 제거 후 다시 생성
                shutil.rmtree(target_path)
                os.makedirs(target_path)
                print(f"[REPLACE] 기존 폴더 삭제 후 재생성 완료: {target_path}")
            elif mode.upper() == "KEEP":
                # 기존 폴더 유지
                print(f"[KEEP] 기존 폴더가 이미 존재하여 유지합니다: {target_path}")
            else:
                print(f"⚠️ 경고: 알 수 없는 모드 '{mode}'입니다. 기존 폴더를 유지합니다.")
        else:
            # 폴더가 없으면 새로 생성
            os.makedirs(target_path)
            print(f"[NEW] 새 폴더 생성 완료: {target_path}")

        return target_path

    except Exception as e:
        print(f"⚠️ NewFolder 오류 발생: {e}")
        return None


def DelFolder(parent_dir, folder_name):
    """
    [#폴더 #삭제 #디렉토리]
    디렉토리) 지정된 위치의 폴더와 그 내부의 모든 내용을 삭제합니다.

    입력 항목:
        parent_dir (str): 부모 디렉토리 경로.
        folder_name (str): 삭제할 폴더명.

    반환값:
        bool: 삭제 성공 여부 (이미 존재하지 않는 경우도 True 반환).

    사용 예제:
        J_File.DelFolder("C:/Project", "01_Temp")

    주의 사항:
        - 폴더 내부의 모든 파일이 영구 삭제되므로 주의가 필요합니다.
        - 다른 프로그램(QGIS, Excel 등)에서 폴더 내 파일을 사용 중이면 삭제되지 않습니다.
    """
    # 1. 절대 경로로 변환
    target_path = os.path.abspath(os.path.join(parent_dir, folder_name))

    try:
        # 2. 존재 여부 확인
        if os.path.exists(target_path):
            if os.path.isdir(target_path):
                # 3. 디렉토리 및 내부 파일 모두 삭제
                shutil.rmtree(target_path)
                print(f"[DELETE] 폴더 삭제 완료: {target_path}")
                return True
            else:
                print(f"⚠️ 경고: '{target_path}'는 폴더가 아닌 파일입니다.")
                return False
        else:
            print(f"[SKIP] 삭제할 폴더가 존재하지 않습니다: {target_path}")
            return True  # 이미 없으므로 성공으로 간주

    except PermissionError:
        print(f"⚠️ 오류: 권한이 없습니다. 폴더나 파일이 다른 프로그램(ArcGIS 등)에서 사용 중인지 확인하세요.")
        return False
    except Exception as e:
        print(f"⚠️ DelFolder 오류 발생: {e}")
        return False


def Split_Path(file_path):
    """
    [#File #Path #Parsing #Utility]
    파일 경로 분해) 전체 경로(String) --> (경로, 파일명, 확장자);
    입력된 파일의 전체 경로를 분석하여 폴더 위치, 파일 이름, 확장자를 각각 분리하여 반환합니다.

    단계별 프로세스:
        1단계 [Absolute-Path]: 입력된 경로를 절대 경로로 변환하여 경로 누락을 방지합니다.
        2단계 [Directory-Extraction]: 파일이 포함된 부모 디렉터리 경로를 추출합니다.
        3단계 [Name-Extension-Split]: 파일명에서 마지막 마침표(.)를 기준으로 순수 이름과 확장자를 분리합니다.

    입력 항목:
        file_path (str): 분해할 파일의 전체 경로 또는 파일명.

    반환값:
        tuple: (folder_path, file_name, extension)
        - folder_path: 파일이 위치한 디렉터리 경로
        - file_name: 확장자를 제외한 파일 이름
        - extension: 마침표(.)를 포함한 파일 확장자

    특징:
        - [경로 정규화]: 입력된 경로의 슬래시(/)와 역슬래시(\\)를 현재 OS 환경에 맞게 자동 정정합니다.
        - [다중 마침표 대응]: 파일명에 마침표가 여러 개 포함되어 있어도 마지막 마침표를 기준으로 정확히 확장자를 추출합니다.

    사용 예제:
        # 1. 개별 인덱싱 접근 방식 (사용자 선호 방식)
        path = "C:/User/Documents/Project/Road_Data.v1.gpkg"
        folder_dir = J_File.Split_Path(path)[0]  # C:\\User\\Documents\\Project
        pure_name  = J_File.Split_Path(path)[1]  # Road_Data.v1
        ext_name   = J_File.Split_Path(path)[2]  # .gpkg

        # 2. 다중 변수 할당 방식 (Unpacking)
        dir_path, file_nm, ext = J_File.Split_Path(path)

        # 3. 실무 응용 (파일명 뒤에 접미사 붙여서 새 경로 만들기)
        new_output = os.path.join(dir_path, f"{file_nm}_Fixed{ext}")
        # 결과: C:\\User\\Documents\\Project\\Road_Data.v1_Fixed.gpkg
    """

    try:
        # 절대 경로로 정규화 (역슬래시 등 OS 차이 해결)
        abs_path = os.path.abspath(file_path)

        folder_path = os.path.dirname(abs_path)
        base_name = os.path.basename(abs_path)

        # 파일명과 확장자 분리 (마지막 마침표 기준)
        file_name, extension = os.path.splitext(base_name)

        # (경로, 파일명, 확장자) 순서로 반환
        return folder_path, file_name, extension

    except Exception as e:
        print(f"🔥 Split_Path 오류: {str(e)}")
        return "", "", ""

def clean_float_strict(value):
    """
    [#숫자 #정밀추출 #데이터정제]
    문자열) 물자열에서 숫자 부분 추출; 문자열이나 혼합 데이터에서 숫자(실수) 부분만 정밀하게 추출합니다.

    입력 항목:
        value (any): 숫자, 문자열, 혹은 None 등 정제가 필요한 값.

    반환값:
        float: 추출된 실수값 (추출 실패 시 0.0 반환).

    사용 예제:
        J_File.clean_float_strict("현재 온도: 18.50도")

    주의 사항:
        - 문자열 내에 여러 숫자가 있을 경우 가장 처음에 발견되는 숫자를 반환합니다.
        - 소수점 손실이 없도록 파이썬 내장 float 정밀도를 유지합니다.
        - 빈 값, None, 혹은 숫자가 없는 문자열은 예외 없이 0.0을 반환하여 계산 오류를 방지합니다.
    """
    if value is None or value == 'None' or str(value).strip() == '': return 0.0
    if isinstance(value, (int, float)): return float(value)
    try:
        found = re.findall(r"[-+]?\d*\.\d+|\d+", str(value))
        return float(found[0]) if found else 0.0
    except:
        return 0.0


def DxfToGpkg(dxf_path, output_path, geometry_type="Line", epsg=5186):
    """
    [#CAD #DXF #변환 #GPKG]
    파일변환) DXF --> GPKG; DXF 파일을 읽어 지정된 형상(점, 선, 면)의 GPKG 파일로 변환합니다.

    입력 항목:
        dxf_path (str): 원본 DXF 파일 경로.
        output_path (str): 저장할 GPKG 파일 경로.
        geometry_type (str): 추출할 형상 타입 ('POINT', 'LINE', 'MULTILINE', 'POLYGON').
        epsg (int): 좌표계 코드 (기본값 5186, 중부원점).

    반환값:
        bool: 변환 성공 시 True, 실패 시 False.

    사용 예제:
        J_File.DxfToGpkg("./input.dxf", "./output.gpkg", "LINE", epsg=5186)

    주의 사항:
        - 블록(INSERT) 속성 객체를 자동으로 분해(Virtual Entities)하여 내부 형상까지 정밀하게 추출합니다.
        - CAD 특성을 고려하여 선의 시작점과 끝점이 1.0m 이내일 경우 POLYGON으로 변환 가능하도록 처리합니다.
        - 모든 데이터는 Z값을 포함한 3D 좌표 정밀도를 유지하며 추출됩니다.
        - 결과물에는 레이어명과 DXF 원본 속성들이 포함됩니다.
    """

    abs_dxf = os.path.abspath(dxf_path).replace("\\", "\\\\")
    abs_out = os.path.abspath(output_path).replace("\\", "\\\\")

    print(f"🔍 {geometry_type} 정밀 추출 시작 (블록 분해 포함)")
    try:
        if os.path.exists(abs_out):
            try:
                os.remove(abs_out)
            except:
                pass

        doc = ezdxf.readfile(abs_dxf)
        msp = doc.modelspace()
        data_list = []
        g_type = geometry_type.upper()

        # 블록 분해를 포함한 엔티티 리스트 생성
        entities = []
        for e in msp:
            if e.dxftype() == 'INSERT':
                entities.extend(e.virtual_entities())
            else:
                entities.append(e)

        for e in entities:
            e_type = e.dxftype().upper()
            attr = {}

            # 모든 속성 저장
            for attr_name in e.dxf.all_existing_dxf_attribs():
                val = e.dxf.get(attr_name)
                attr[f"dxf_{attr_name}"] = str(val) if isinstance(val, (tuple, list, ezdxf.math.Vec3)) else val

            attr['original_type'] = e_type
            attr['layer'] = e.dxf.layer

            # --- [형상 추출 시작] ---
            geom = None
            if e_type in ['LWPOLYLINE', 'POLYLINE', 'LINE']:
                # 1. pnts 변수 정의 (선언 위치 확보)
                pnts = []
                if e_type == 'LINE':
                    pnts = [(e.dxf.start.x, e.dxf.start.y, e.dxf.start.z), (e.dxf.end.x, e.dxf.end.y, e.dxf.end.z)]
                elif e_type == 'LWPOLYLINE':
                    elev = e.dxf.elevation if e.has_dxf_attrib('elevation') else 0.0
                    pnts = [(p[0], p[1], elev) for p in e.get_points()]
                else:  # POLYLINE (2D or 3D)
                    pnts = [(v.dxf.location.x, v.dxf.location.y, v.dxf.location.z) for v in e.vertices]

                # 2. pnts가 생성되었을 때만 길이 및 유효성 체크
                if len(pnts) < 2: continue

                # [2026-01-01 무손실] 실제 누적 길이 계산 (폐합선은 살리고 유령선만 제거)
                total_dist = 0
                for i in range(len(pnts) - 1):
                    p1, p2 = pnts[i], pnts[i + 1]
                    total_dist += ((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2 + (p2[2] - p1[2]) ** 2) ** 0.5

                # 길이가 먼지 수준(1e-9) 이하면 과감히 제외하여 RuntimeWarning 차단
                if total_dist <= 1e-9:
                    continue

                is_closed = e.closed if hasattr(e, 'closed') else False
                dist_2d = ((pnts[0][0] - pnts[-1][0]) ** 2 + (pnts[0][1] - pnts[-1][1]) ** 2) ** 0.5

                if g_type == "POLYGON":
                    if is_closed or dist_2d < 1.0:
                        if pnts[0] != pnts[-1]: pnts.append(pnts[0])
                        geom = Polygon(pnts)
                elif g_type in ["LINE", "MULTILINE"]:
                    geom = LineString(pnts)
                    attr['is_closed'] = str(is_closed)

            elif g_type == "POINT":
                pos = getattr(e.dxf, 'insert', getattr(e.dxf, 'location', None))
                if pos:
                    geom = Point(pos.x, pos.y, pos.z)

            if geom:
                attr['geometry'] = geom
                data_list.append(attr)

        # --- [결과 저장] ---
        if not data_list:
            print(f"❌ {geometry_type}에 해당하는 데이터가 없습니다.")
            return False

        gdf = gpd.GeoDataFrame(data_list, crs=f"EPSG:{epsg}")

        # [2026-01-09] 디렉터리 자동 생성
        out_dir = os.path.dirname(abs_out)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        gdf.to_file(abs_out, driver='GPKG', engine='pyogrio')
        print(f"✅ {geometry_type} 추출 성공: {os.path.basename(abs_out)}")
        return True

    except Exception as e:
        # [2026-01-27] 에러 메시지 경로 보정
        err_msg = str(e).replace("\\", "\\\\")
        print(f"⚠️ 추출 오류: {err_msg}")
        return False


def GpkgToDxf(gpkg_path, dxf_path):
    """
    [#CAD #DXF #GPKG #변환 #복구]
    파일변환) GPKG --> DXF; GPKG 공간 데이터를 속성이 유지된 DXF 캐드 파일로 변환합니다.

    입력 항목:
        gpkg_path (str): 원본 GPKG 파일 경로.
        dxf_path (str): 저장할 DXF 파일 경로.

    반환값:
        bool: 변환 성공 시 True, 실패 시 False.

    사용 예제:
        J_File.GpkgToDxf("./input.gpkg", "./output.dxf")

    주의 사항:
        - GPKG 내의 'layer', 'dxf_color', 'original_type' 등의 속성을 참조하여 원본 캐드 스타일을 복구합니다.
        - Point 데이터 중 'text_content' 속성이 있는 경우 TEXT 객체로, 'block_name'이 있는 경우 블록으로 생성합니다.
        - 3D Polyline 여부(is_3d_polyline)에 따라 적절한 엔티티 타입(LWPOLYLINE 또는 POLYLINE3D)으로 변환합니다.
        - 저장될 폴더가 존재하지 않을 경우 자동으로 생성합니다.
    """
    if not os.path.exists(gpkg_path): return False
    print(f"🔄 타입별 맞춤 복구 시작: {gpkg_path}")
    try:
        gdf = gpd.read_file(gpkg_path)
        if gdf.empty: return False

        doc = ezdxf.new('R2000')
        doc.header['$INSUNITS'] = 6
        msp = doc.modelspace()

        # 사전 설정 (레이어, 스타일)
        if 'layer' in gdf.columns:
            for l in gdf['layer'].unique():
                if l and str(l) not in doc.layers: doc.layers.new(name=str(l))
        if 'dxf_style' in gdf.columns:
            for s in gdf['dxf_style'].dropna().unique():
                if s and str(s) not in doc.styles: doc.styles.new(str(s), dxfattribs={'font': 'romans.shx'})

        for idx, row in gdf.iterrows():
            geom = row.geometry
            if geom is None: continue

            layer = str(row.get('layer', '0'))
            try:
                c_val = row.get('dxf_color', 256)
                color = int(clean_float_strict(c_val))
            except:
                color = 256
            dxf_attribs = {'layer': layer, 'color': color if 0 <= color <= 256 else 256}

            orig_type = str(row.get('original_type', 'LINE')).upper()
            is_3d = str(row.get('is_3d_polyline', 'False')).upper() == 'TRUE'

            # -----------------------------------------------------------
            # 1. [핵심] 선형 데이터 분기 처리 (LINE / 3D POLY / 2D POLY)
            # -----------------------------------------------------------
            if geom.geom_type in ['LineString', 'Polygon']:
                # 좌표 추출
                if geom.geom_type == 'Polygon':
                    pnts_3d = [(float(p[0]), float(p[1]), float(p[2]) if len(p) > 2 else 0.0) for p in geom.exterior.coords]
                else:
                    pnts_3d = [(float(p[0]), float(p[1]), float(p[2]) if len(p) > 2 else 0.0) for p in geom.coords]

                # A. 3D Polyline
                if orig_type == 'POLYLINE' and is_3d:
                    entity = msp.add_polyline3d(pnts_3d, dxfattribs=dxf_attribs)
                    if geom.geom_type == 'Polygon' or str(row.get('is_closed', '')).upper() == 'TRUE':
                        entity.closed = True

                # B. 일반 LINE 복원 (조건 강화!)
                # [수정] Polygon인 경우는 절대 LINE으로 그리지 않도록 geom_type 체크 추가
                elif orig_type == 'LINE' and len(pnts_3d) >= 2 and geom.geom_type != 'Polygon':
                    msp.add_line(pnts_3d[0], pnts_3d[-1], dxfattribs=dxf_attribs)

                # C. 2D Polyline / Polygon (버퍼는 이리로 와야 함)
                else:
                    pnts_2d = [(p[0], p[1]) for p in pnts_3d]
                    entity = msp.add_lwpolyline(pnts_2d, dxfattribs=dxf_attribs)

                    # 속성 복원
                    entity.dxf.elevation = clean_float_strict(row.get('dxf_elevation', 0.0))
                    width = clean_float_strict(row.get('dxf_const_width', 0.0))
                    if width > 0: entity.dxf.const_width = width

                    # Polygon이거나 닫힌 속성이면 닫기
                    if geom.geom_type == 'Polygon' or str(row.get('is_closed', '')).upper() == 'TRUE':
                        entity.closed = True

            # -----------------------------------------------------------
            # 2. 점형 데이터 처리 (TEXT / INSERT / POINT)
            # -----------------------------------------------------------
            elif geom.geom_type == 'Point':
                # [수정됨] Z값이 없는 2D Point도 처리할 수 있도록 안전 장치 추가
                x, y = float(geom.x), float(geom.y)
                z = float(geom.z) if geom.has_z else 0.0  # Z가 있으면 쓰고, 없으면 0.0

                if 'text_content' in row and pd.notna(row['text_content']):
                    t = msp.add_text(str(row['text_content']), dxfattribs=dxf_attribs)
                    t.set_placement((x, y, z))
                    # 텍스트 높이 우선순위: text_height > dxf_height > 4.0
                    h = clean_float_strict(row.get('text_height', 0))
                    if h == 0: h = clean_float_strict(row.get('dxf_height', 4.0))
                    t.dxf.height = h
                    t.dxf.rotation = clean_float_strict(row.get('dxf_rotation', 0.0))
                    if 'dxf_style' in row: t.dxf.style = str(row['dxf_style'])

                elif 'block_name' in row and pd.notna(row['block_name']):
                    b_name = str(row['block_name'])
                    if b_name not in doc.blocks:
                        blk = doc.blocks.new(name=b_name)
                        blk.add_circle((0, 0), radius=0.1)
                    ins = msp.add_blockref(b_name, (x, y, z), dxfattribs=dxf_attribs)
                    ins.dxf.xscale = clean_float_strict(row.get('dxf_xscale', 1.0))
                    ins.dxf.yscale = clean_float_strict(row.get('dxf_yscale', 1.0))
                    if 'dxf_rotation' in row: ins.dxf.rotation = clean_float_strict(row['dxf_rotation'])

                else:
                    msp.add_point((x, y, z), dxfattribs=dxf_attribs)

        # [추가] 폴더가 없으면 생성
        os.makedirs(os.path.dirname(dxf_path), exist_ok=True)

        doc.saveas(dxf_path)
        print(f"✅ 복구 완료: {dxf_path}")
        return True
    except Exception as e:
        print(f"⚠️ 오류: {e}");
        return False


def ShpToGpkg(shp_path, gpkg_path, epsg=5186):
    """
    [#GIS #SHP #GPKG #변환]
    파일변환) Shape --> GPKG; 쉐이프파일(SHP)을 읽어 GeoPackage(GPKG) 형식으로 변환합니다.

    입력 항목:
        shp_path (str): 원본 SHP 파일 경로.
        gpkg_path (str): 저장할 GPKG 파일 경로.
        epsg (int): 좌표계가 없을 경우 정의할 기본 EPSG 코드 (기본값 5186).

    반환값:
        bool: 변환 성공 시 True, 실패 시 False.

    사용 예제:
        J_File.ShpToGpkg("./input.shp", "./output.gpkg")

    주의 사항:
        - 한글 깨짐 방지를 위해 cp949와 utf-8 인코딩을 순차적으로 시도합니다.
        - 사용자 원칙에 따라 데이터 소수점 손실 방지를 위해 pyogrio 엔진을 사용합니다.
        - 저장될 폴더가 존재하지 않을 경우 자동으로 생성합니다.
        - 레이어 명칭은 원본 파일명을 따라 자동으로 설정됩니다.
    """
    gdf = None
    encodings_to_try = ['UTF-8', 'CP949']

    for enc in encodings_to_try:
        try:
            os.environ['SHAPE_ENCODING'] = enc
            gdf = gpd.read_file(shp_path, engine='pyogrio', encoding=enc)

            if gdf is not None and not gdf.empty:
                print(f"👉 메모리 강제 인코딩({enc})으로 정상 로드 완료")
                break

        except Exception as e:
            # e를 출력하여 숨겨진 진짜 에러 메시지를 확인합니다!
            print(f"⚠️ {enc} 읽기 실패 (사유: {e})")
            continue
        finally:
            if 'SHAPE_ENCODING' in os.environ:
                del os.environ['SHAPE_ENCODING']

    # 🚨 빈 파일(객체 없음) 발견 시 로직 복원
    if gdf is None or gdf.empty:
        # 알림창 띄우기: [확인(OK)] = True(무시), [취소(Cancel)] = False(중단)
        user_choice = messagebox.askokcancel(
            title="빈 데이터 알림",
            message=f"파일을 읽을 수 없거나 데이터(객체)가 없습니다.\n\n파일명: {os.path.basename(shp_path)}\n\n이 파일을 무시하고 다음으로 넘어가시겠습니까?\n(취소를 누르면 전체 작업이 중단됩니다.)"
        )

        if user_choice:
            # '확인(무시)' 누름 -> 에러 없이 False를 반환하여 메인 루프가 다음 파일로 넘어가게 유도
            print(f"⏭️ 빈 파일 무시됨: {os.path.basename(shp_path)}")
            return False
        else:
            # '취소' 누름 -> 에러를 발생시켜 프로그램(메인 루프) 튕기게 함
            raise RuntimeError(f"사용자가 빈 파일 변환 작업을 취소했습니다: {os.path.basename(shp_path)}")

    try:
        # 좌표계(CRS) 설정
        if gdf.crs is None:
            gdf.set_crs(epsg=int(epsg), inplace=True, allow_override=True)
        elif str(epsg) not in str(gdf.crs):
            gdf = gdf.to_crs(epsg=int(epsg))

        # 저장 경로 생성 및 GPKG 저장
        os.makedirs(os.path.dirname(gpkg_path), exist_ok=True)
        layer_name = os.path.splitext(os.path.basename(shp_path))[0]

        try:
            gdf.to_file(gpkg_path, layer=layer_name, driver='GPKG', engine='pyogrio')
        except Exception:
            gdf.to_file(gpkg_path, layer=layer_name, driver='GPKG', engine='fiona')

        if os.path.exists(gpkg_path):
            return True
        else:
            raise FileNotFoundError("GPKG 파일 저장 실패")

    except Exception as e:
        raise RuntimeError(f"GPKG 변환 중단: {str(e)}")

def GpkgToShp(gpkg_path, shp_path, encoding_opt="UTF-8"):
    """
    [#GIS #GPKG #SHP #변환]
    파일변환) GPKG --> Shpae; GeoPackage(GPKG) 데이터를 읽어 쉐이프파일(SHP) 형식으로 변환합니다.

    입력 항목:
        gpkg_path (str): 원본 GPKG 파일 경로.
        shp_path (str): 저장할 SHP 파일 경로.

    반환값:
        bool: 변환 성공 시 True, 실패 시 False.

    사용 예제:
        J_File.GpkgToShp("./input.gpkg", "./output.shp")

    주의 사항:
        - 쉐이프파일의 특성을 고려하여 한글 필드명 유지를 위해 'cp949' 인코딩을 적용합니다.
        - 사용자 원칙에 따라 데이터 소수점 손실 방지를 위해 pyogrio 엔진을 사용합니다.
        - 저장될 폴더가 존재하지 않을 경우 자동으로 생성합니다.
        - SHP 형식의 제약사항(필드명 10자 제한 등)이 적용될 수 있음에 유의하십시오.
    """
    try:

        src = Path(gpkg_path).resolve()
        dst = Path(shp_path).resolve()
        if not src.exists(): return False

        # 1. 데이터 로드
        gdf = gpd.read_file(str(src), engine='pyogrio')
        if len(gdf) == 0: return True

        # 2. [정밀 세척] (기존 로직 동일)
        for col in gdf.columns:
            if col != 'geometry':
                if gdf[col].dtype == 'object' or gdf[col].dtype == 'string':
                    gdf[col] = gdf[col].fillna("")
                gdf[col] = gdf[col].astype(str).apply(
                    lambda x: "" if x.strip().lower() in ['none', 'nan', 'null', '<na>'] else x
                )
                gdf[col] = gdf[col].str.replace(r'\.0$', '', regex=True)

        # 3. 폴더 생성
        dst.parent.mkdir(parents=True, exist_ok=True)

        # 4. 저장 (최대한 UTF-8 유도)
        # fiona.Env와 to_file의 encoding을 모두 동일하게 맞춥니다.
        enc = encoding_opt.lower()
        with fiona.Env(SHAPE_ENCODING=enc, GDAL_FILENAME_IS_UTF8='YES'):
            try:
                gdf.to_file(str(dst), driver='ESRI Shapefile', encoding=enc, engine='fiona')
            except:
                gdf.to_file(str(dst), driver='ESRI Shapefile', encoding=enc, engine='pyogrio')

        # 5. [강력 보정] CPG 파일 내용 강제 교체
        cpg_path = dst.with_suffix('.cpg')

        # 파일이 생성될 때까지 아주 짧게 대기 (0.1초)
        time.sleep(0.1)

        # 기존 파일을 지우고 새로 만들어 버립니다. (덮어쓰기보다 확실함)
        if cpg_path.exists():
            cpg_path.unlink()  # 기존 파일 삭제

        with open(str(cpg_path), 'w', encoding='ascii') as f:
            # .cpg 파일은 대문자로 쓰는 것이 표준입니다.
            f.write(encoding_opt.upper())

        print(f"⚠️ [인코딩강제] {dst.name}: .cpg 내용을 '{encoding_opt.upper()}'로 강제 고정함")

        # 6. 검증
        if dst.exists():
            return True
        return False

    except Exception as e:
        print(f"🔥 GpkgToShp 오류: {str(e).replace('\\', '\\\\')}")
        return False

def CopyGPKG_IfNotEmpty(source_path, target_path, circle_diameter=1.0):
    """
    [#GIS #파일복사 #GPKG #DXF #검수]
    복사) 객체가 있을 경우 복사(GPKG,DXF); 객체가 존재하는 경우에만 GPKG를 복사하고, 점 데이터를 원(Circle)으로 변환한 DXF를 생성합니다.

    입력 항목:
        source_path (str): 원본 GPKG 파일 경로.
        target_path (str): 저장할 GPKG 파일 경로 (확장자 포함).
        circle_diameter (float): DXF 변환 시 점(Point) 데이터를 대체할 원의 지름 (기본값 1.0).

    반환값:
        bool: 복사 및 변환 성공 시 True, 객체가 없거나 실패 시 False.

    사용 예제:
        J_File.CopyGPKG_IfNotEmpty("./source.gpkg", "./check/result.gpkg", 1.0)

    주의 사항:
        - 원본 GPKG에 객체가 1개 이상 존재할 때만 동작하여 불필요한 빈 파일 생성을 방지합니다.
        - GPKG 복사본과 동일한 경로에 확장자만 다른 DXF 파일이 자동으로 생성됩니다.
        - DXF 생성 시 점(Point) 데이터는 AutoCAD에서 인식 가능한 실제 CIRCLE 객체로 변환됩니다.
        - 저장될 폴더가 존재하지 않을 경우 사용자 원칙에 따라 자동으로 생성합니다.
    """
    if not os.path.exists(source_path):
        print(f"⚠️ 원본 파일이 없습니다: {source_path}")
        return False

    try:
        # 1. 메타데이터 확인
        layer_names = fiona.listlayers(source_path)
        if not layer_names: return False
        layer_name = layer_names[0]

        with fiona.open(source_path, layer=layer_name) as src:
            feature_count = len(src)

        if feature_count > 0:
            # 폴더 생성 및 GPKG 복사 (원본 유지)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            shutil.copy2(source_path, target_path)

            # 2. DXF 직접 생성을 위한 데이터 로드
            gdf = gpd.read_file(target_path, engine='pyogrio')
            dxf_path = os.path.splitext(target_path)[0] + ".dxf"

            # DXF 문서 설정
            doc = ezdxf.new('R2000')
            msp = doc.modelspace()
            radius = circle_diameter / 2.0  # 지름 1 -> 반지름 0.5

            for _, row in gdf.iterrows():
                geom = row.geometry
                if geom is None: continue

                # 기본 속성 (레이어 등)
                layer = str(row.get('layer', '0'))
                if layer not in doc.layers:
                    doc.layers.new(name=layer)

                dxf_attribs = {'layer': layer}

                # --- 기하 타입별 처리 ---
                if geom.geom_type == 'Point':
                    # [핵심] 점 데이터는 진짜 CIRCLE로 생성
                    x, y = float(geom.x), float(geom.y)
                    z = float(geom.z) if geom.has_z else 0.0
                    # AutoCAD에서 진짜 원(CIRCLE)으로 인식됨
                    msp.add_circle((x, y, z), radius=radius, dxfattribs=dxf_attribs)

                elif geom.geom_type in ['LineString', 'MultiLineString']:
                    # 선 데이터 처리 (MultiLine 대응)
                    lines = [geom] if geom.geom_type == 'LineString' else geom.geoms
                    for line in lines:
                        pnts = list(line.coords)
                        if len(pnts) >= 2:
                            msp.add_lwpolyline(pnts, dxfattribs=dxf_attribs)

                elif geom.geom_type in ['Polygon', 'MultiPolygon']:
                    # 면 데이터 처리 (외곽선 위주)
                    polys = [geom] if geom.geom_type == 'Polygon' else geom.geoms
                    for poly in polys:
                        pnts = list(poly.exterior.coords)
                        if len(pnts) >= 2:
                            msp.add_lwpolyline(pnts, dxfattribs=dxf_attribs).closed = True

            # DXF 저장
            doc.saveas(dxf_path)

            print(f"✅ 완료: GPKG 복사 및 DXF(Circle변환) 생성 완료 ({os.path.basename(dxf_path)})")
            return True
        else:
            return False

    except Exception as e:
        print(f"❌ CopyGPKG 오류: {e}")
        return False


def clean_eo_file(input_path, output_path): # EO값 정제
    """
    [#데이터정제 #EO #TXT #무손실]
    EO값정리) 불규칙한 공백이나 탭으로 구분된 EO 파일을 표준 쉼표(,) 구분 형식으로 정제합니다.

    입력 항목:
        input_path (str): 원본 EO 데이터 파일 경로 (TXT 등).
        output_path (str): 정제 후 저장할 파일 경로.

    반환값:
        bool: 정제 및 저장 성공 시 True, 실패 시 False.

    사용 예제:
        J_File.clean_eo_file("./EO_raw.txt", "./EO_clean.csv")

    주의 사항:
        - 사용자 원칙에 따라 데이터 소수점 손실을 방지하기 위해 모든 수치를 문자열(String) 단위로 처리합니다.
        - 값 내부에 포함된 언더바('_') 문자를 자동으로 제거하여 수치 데이터의 가독성을 높입니다.
        - 입력 파일의 인코딩(UTF-8, CP949)을 자동으로 판별하여 읽어옵니다.
        - 저장될 폴더가 존재하지 않을 경우 사용자 원칙에 따라 자동으로 생성합니다.
        - 출력 파일 상단에는 표준 헤더(Name, X, Y, Z, ω, φ, κ)가 자동으로 삽입됩니다.
    """
    header = "Name,X,Y,Z,ω,φ,κ\n"

    if not os.path.exists(input_path):
        print(f"⚠️ 원본 파일을 찾을 수 없습니다: {input_path}")
        return False

    try:
        # 1. 원본 파일 읽기 (인코딩 대응: UTF-8 -> CP949)
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            with open(input_path, 'r', encoding='cp949') as f:
                lines = f.readlines()

        clean_data = []
        for line in lines:
            line = line.strip()
            # 빈 줄이나 이미 헤더가 포함된 줄은 제외
            if not line or "Name" in line:
                continue

            # [핵심] split()으로 분리 후 각 요소에서 '_' 제거
            # 소수점 손실을 방지하기 위해 float 변환 없이 문자열 상태에서 replace 수행
            parts = [p.replace('_', '') for p in line.split()]

            # 좌표 및 속성 데이터가 7개 이상인 경우만 정제하여 추가
            if len(parts) >= 7:
                # 데이터 무손실 유지를 위해 문자열 그대로 쉼표 연결
                clean_data.append(",".join(parts[:7]))

        # 2. 정제된 내용을 저장 파일로 기록
        # [지침 반영] 폴더가 없으면 자동으로 생성
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(header)
            f.write("\n".join(clean_data))

        print(f"✅ EO 파일 정제 완료 (특수문자 제거 포함): {output_path}")
        return True

    except Exception as e:
        print(f"⚠️ clean_eo_file 오류: {e}")
        return False


def get_epsg_code(file_path):
    """
    [#GIS #좌표계 #EPSG #WKT #분석]
    좌표계) 좌표계 추출; 공간 데이터(SHP, GPKG)의 메타데이터를 분석하여 한국 표준 EPSG 코드를 추출합니다.

    입력 항목:
        file_path (str): 좌표계 정보를 추출할 데이터 파일 경로.

    반환값:
        str: 판별된 EPSG 코드 문자열 (판별 불가 시 None).

    사용 예제:
        epsg_code = J_File.get_epsg_code("./data/area.gpkg")

    주의 사항:
        - pyogrio 엔진을 사용하여 파일의 첫 번째 행만 로드하므로 대용량 파일도 빠르게 분석합니다.
        - 단순 코드 확인 외에도 WKT 내의 원점 경도(Central Meridian)와 가산치(False Northing)를 분석하여 코드를 강제로 찾아냅니다.
        - 중부원점(5186), 동부원점(5187), UTM-K(5179) 등 한국 주요 좌표계를 우선적으로 판별합니다.
        - WKT 문자열의 공백 및 따옴표를 모두 제거한 후 비교하므로 포맷 차이에 따른 오류를 방지합니다.
    """
    if not os.path.exists(file_path):
        return None

    try:
        # 1. 파일 읽기 (메타데이터만 로드)
        gdf = gpd.read_file(file_path, rows=1, engine='pyogrio')
        if not gdf.crs:
            return None

        # 2. 표준 EPSG 코드 추출 시도 (가장 정확)
        epsg = gdf.crs.to_epsg()
        if epsg:
            return str(epsg)

        # 3. WKT 텍스트 정밀 분석 (띄어쓰기 무시 로직)
        # 모든 공백을 제거하고 대문자로 변환하여 비교 (띄어쓰기 변수 차단)
        raw_wkt = gdf.crs.to_wkt().upper()
        clean_wkt = raw_wkt.replace(" ", "").replace('"', "")
        # 예: PARAMETER["central_meridian",129] -> PARAMETER[CENTRAL_MERIDIAN,129]

        # --- 핵심 파라미터 존재 여부 확인 ---

        # 가산치 (False Northing) 600,000 (2010년 이후 신규 보정)
        is_600k = "FALSE_NORTHING,600000" in clean_wkt or "FALSENORTHING,600000" in clean_wkt

        # 가산치 500,000 (구 좌표계)
        is_500k = "FALSE_NORTHING,500000" in clean_wkt or "FALSENORTHING,500000" in clean_wkt

        # --- 원점 경도(Central Meridian)에 따른 코드 반환 ---

        # 1. 동부원점 (129도) -> 사용자님 케이스 (5187)
        if "CENTRAL_MERIDIAN,129" in clean_wkt:
            if is_600k: return "5187"  # 동부원점 (신)
            if is_500k: return "5183"  # 동부원점 (구)

        # 2. 동해원점 (131도) -> 5188
        if "CENTRAL_MERIDIAN,131" in clean_wkt:
            return "5188"

        # 3. 서부원점 (125도) -> 5185
        if "CENTRAL_MERIDIAN,125" in clean_wkt:
            if is_600k: return "5185"
            if is_500k: return "5180"

        # 4. 중부원점 (127도) -> 5186
        if "CENTRAL_MERIDIAN,127" in clean_wkt:
            # UTM-K (127.5)와 혼동 방지를 위해 정확히 127인지 확인
            if "CENTRAL_MERIDIAN,127.5" in clean_wkt:
                return "5179"

            if is_600k: return "5186"  # 중부원점 (신)
            if is_500k: return "5181"  # 중부원점 (구)

        # 5. 그래도 못 찾았는데 TM 투영이고 가산치가 60만/20만이다?
        # WKT 구조가 특이해도 값만 맞으면 5187로 추정 (사용자님 데이터 맞춤)
        if "TRANSVERSE_MERCATOR" in clean_wkt:
            if "200000" in clean_wkt and "600000" in clean_wkt:
                # 경도 129가 텍스트 어딘가에 있으면 5187
                if "129" in clean_wkt:
                    return "5187"

        # 위경도 (WGS84)
        if "GEOGCS" in clean_wkt and "WGS84" in clean_wkt and "PROJECTION" not in clean_wkt:
            return "4326"

        return None

    except Exception as e:
        print(f"⚠️ CRS 분석 오류: {e}")
        return None


def CopyFilesByField(gpkg_path, output_gpkg_name, field_name, src_dir, dst_dir, extensions="*"):
    """
    [#파일복사 #데이터필터링 #GPKG #매칭]
    파일복사) 필드내용 참조, 파일복사, 복사EO값정리; GPKG 필드값과 매칭되는 파일을 찾아 복사하고, 성공한 내역만 모아 새 GPKG로 저장합니다.

    입력 항목:
        gpkg_path (str): 대상 속성이 포함된 원본 GPKG 경로.
        output_gpkg_name (str): 복사 성공 리스트를 저장할 새 GPKG 경로.
        field_name (str): 파일 이름과 매칭할 값이 들어있는 필드명.
        src_dir (str): 원본 파일들이 위치한 소스 디렉토리.
        dst_dir (str): 파일을 복사하여 저장할 대상 디렉토리.
        extensions (str/list): 필터링할 확장자 (기본값 "*"는 모든 파일, ".tif" 등 지정 가능).

    반환값:
        str: 생성된 결과 GPKG의 절대 경로 (복사된 파일이 없거나 실패 시 None).

    사용 예제:
        J_File.CopyFilesByField("./input.gpkg", "./result_list.gpkg", "IMG_NAME", "./Origin_Img", "./Copy_Img", ".tif")

    주의 사항:
        - 하위 폴더를 포함하여 소스 디렉토리를 전수 조사(os.walk)하며, 원본의 폴더 구조를 유지하며 복사합니다.
        - 사용자 원칙에 따라 데이터 소수점 및 문자열 손실 방지를 위해 pyogrio 엔진을 사용합니다.
        - 파일 복사 시 필드값을 파일명으로 변경하여 저장하며, 중복 복사를 방지하는 로직이 포함되어 있습니다.
        - 저장될 대상 폴더(`dst_dir`)나 결과 GPKG 폴더가 존재하지 않을 경우 자동으로 생성합니다.
    """

    if not os.path.exists(gpkg_path):
        print(f"⚠️ 원본 GPKG를 찾을 수 없습니다: {gpkg_path}")
        return None

    try:
        # 1. GPKG 데이터 로드 (문자열 손실 방지)
        gdf = gpd.read_file(gpkg_path, engine='pyogrio')

        # 복사된 데이터의 인덱스를 추적하기 위한 리스트
        copied_indices = []

        # 확장자 필터 설정
        if isinstance(extensions, str):
            ext_list = None if extensions == "*" else [extensions.lower()]
        else:
            ext_list = [e.lower() for e in extensions]

        # 2. 파일 시스템 스캔 (성능을 위해 소스 디렉토리를 한 번만 순회)
        # 파일명을 키로, 경로를 값으로 갖는 사전 생성
        file_map = {}
        for root, _, files in os.walk(src_dir):
            for f in files:
                file_map[f] = os.path.join(root, f)

        # 3. GPKG 행 순회하며 복사 진행
        for idx, row in gdf.iterrows():
            val = str(row[field_name])
            if not val or val == 'None':
                continue

            # 소스 디렉토리 내 파일들 중 val이 포함된 파일 찾기
            for filename, src_file_path in file_map.items():
                file_lower = filename.lower()

                # 확장자 및 키워드 매칭 확인
                is_ext_match = (ext_list is None) or any(file_lower.endswith(e.replace("*", "")) for e in ext_list)

                if is_ext_match and (val in filename):
                    file_ext = os.path.splitext(filename)[1]
                    new_filename = f"{val}{file_ext}"

                    # 대상 경로 설정 (지침 반영: 디렉토리 자동 생성)
                    relative_path = os.path.relpath(os.path.dirname(src_file_path), src_dir)
                    target_folder = os.path.join(dst_dir, relative_path)
                    os.makedirs(target_folder, exist_ok=True)

                    dst_file_path = os.path.join(target_folder, new_filename)

                    # 파일 복사
                    if not os.path.exists(dst_file_path):
                        shutil.copy2(src_file_path, dst_file_path)

                    # 복사 성공 리스트에 인덱스 추가 (GPKG 필터링용)
                    copied_indices.append(idx)
                    break  # 한 행(val)에 대해 파일 하나만 처리

        # 4. 복사된 데이터만 추출하여 새로운 GPKG 저장
        if copied_indices:
            new_gdf = gdf.loc[copied_indices].copy()

            # 저장 디렉토리 확인 및 생성
            output_dir = os.path.dirname(output_gpkg_name)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            # 새 GPKG 저장
            new_gdf.to_file(output_gpkg_name, driver="GPKG", engine='pyogrio')
            print(f"✅ 새 GPKG 저장 완료: {output_gpkg_name} ({len(new_gdf)}건)")
            return output_gpkg_name
        else:
            print("⚠️ 복사된 파일이 없어 GPKG를 생성하지 않았습니다.")
            return None

    except Exception as e:
        print(f"⚠️ CopyFilesByField 오류: {e}")
        return None

def ExportToCSV(input_path, output_csv_path):
    """
    [#CSV #좌표 #변환 #데이터추출]
    파일변환) GPKG/Shape --> CSV 변환; 공간 데이터(GPKG/SHP)를 읽어 좌표값이 포함된 CSV 파일로 저장합니다.

    입력 항목:
        input_path (str): 원본 공간 데이터 경로 (SHP, GPKG 등).
        output_csv_path (str): 저장할 CSV 파일 경로.

    반환값:
        bool: 변환 성공 시 True, 실패 시 False.

    사용 예제:
        J_File.ExportToCSV("./Data.gpkg", "./Result.csv")

    주의 사항:
        - Point 데이터의 경우 X, Y, Z 컬럼을 자동으로 생성하여 수치화합니다.
        - 사용자 원칙에 따라 데이터 소수점 손실 방지를 위해 pyogrio 엔진을 사용하여 정밀하게 읽습니다.
        - 엑셀(Excel)에서 한글 깨짐을 방지하기 위해 'utf-8-sig' 인코딩으로 저장합니다.
        - 저장될 폴더가 존재하지 않을 경우 사용자 원칙에 따라 자동으로 생성합니다.
    """
    if not os.path.exists(input_path):
        print(f"⚠️ 입력 파일을 찾을 수 없습니다: {input_path}")
        return False

    try:
        # [핵심 추가] 파일을 읽어서 gdf 변수를 정의합니다.
        # pyogrio 엔진을 사용하여 속도를 높이고 소수점 정밀도를 유지합니다.
        gdf = gpd.read_file(input_path, engine='pyogrio')

        # 1. 좌표 추출 (Point 데이터인 경우에만 X, Y, Z 컬럼 생성)
        if all(gdf.geometry.type == 'Point'):
            # 좌표값을 직접 추출하여 소수점 손실 없이 컬럼 생성
            gdf['X'] = gdf.geometry.x
            gdf['Y'] = gdf.geometry.y
            # Z값이 있으면 추출하고, 없으면 0.0으로 초기화
            gdf['Z'] = gdf.geometry.z if gdf.geometry.has_z.any() else 0.0

        # 2. Geometry 객체 컬럼 제거 (CSV 저장 시 오류 방지)
        df_export = gdf.drop(columns='geometry')

        # 3. CSV 저장
        # index=False: 불필요한 인덱스 번호 생성 방지
        # encoding='utf-8-sig': 엑셀에서 한글이 깨지지 않도록 보정
        df_export.to_csv(output_csv_path, index=False, encoding='utf-8-sig')

        print(f"✅ CSV 변환 완료: {output_csv_path}")
        return True

    except Exception as e:
        print(f"⚠️ CSV 변환 중 오류 발생: {e}")
        return False


def Merge(input_files, output_path):
    """
    [#GIS #데이터병합 #통합 #GPKG]
    객체연산) Merge; 여러 개의 공간 데이터 파일을 하나의 GeoPackage(GPKG) 파일로 병합합니다.

    입력 항목:
        input_files (list): 병합할 파일 경로들의 리스트 (예: [path1, path2, ...]).
        output_path (str): 저장할 통합 GPKG 파일 경로.

    반환값:
        bool: 병합 및 저장 성공 시 True, 실패 시 False.

    사용 예제:
        J_File.Merge(["./zone1.shp", "./zone2.gpkg"], "./total_area.gpkg")

    주의 사항:
        - 병합 시 첫 번째 유효한 파일의 좌표계(CRS)를 기준으로 나머지 데이터들을 자동 변환하여 통합합니다.
        - 사용자 원칙에 따라 데이터 소수점 정밀도 유지를 위해 pyogrio 엔진을 사용합니다.
        - 모든 속성 필드를 유지하며 병합하고, 인덱스는 자동으로 재정렬됩니다.
        - 저장될 폴더가 존재하지 않을 경우 사용자 원칙에 따라 자동으로 생성합니다.
    """
    # 1. 저장 디렉토리 자동 생성
    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)
        print(f"📂 디렉토리 생성 완료: {out_dir}")

    all_gdfs = []
    first_crs = None

    # 2. 모든 파일 로드
    for file_path in input_files:
        if not os.path.exists(file_path):
            print(f"⚠️ 파일을 찾을 수 없습니다: {file_path}")
            continue

        try:
            # 정밀도 유지를 위해 pyogrio 엔진 사용
            gdf = gpd.read_file(file_path, engine='pyogrio')

            if gdf.empty:
                print(f"ℹ️ 빈 파일 건너뜀: {os.path.basename(file_path)}")
                continue

            # 기준 좌표계(CRS) 설정 (첫 번째 유효한 파일 기준)
            if first_crs is None:
                first_crs = gdf.crs
            else:
                # 좌표계가 다를 경우 변환하여 소수점 손실 방지
                if gdf.crs != first_crs:
                    gdf = gdf.to_crs(first_crs)

            all_gdfs.append(gdf)
            print(f"📄 로드 완료: {os.path.basename(file_path)} (행 수: {len(gdf)})")

        except Exception as e:
            print(f"⚠️ 파일 로드 실패 ({os.path.basename(file_path)}): {e}")

    if not all_gdfs:
        print("❌ 병합할 데이터가 없습니다.")
        return False

    try:
        # 3. 데이터 병합 (모든 필드 유지)
        # ignore_index=True를 통해 인덱스를 재정렬합니다.
        merged_gdf = pd.concat(all_gdfs, ignore_index=True)

        # 다시 GeoDataFrame으로 선언 (좌표계 유지)
        merged_gdf = gpd.GeoDataFrame(merged_gdf, crs=first_crs)

        # 4. 결과 저장 (소수점 무손실)
        merged_gdf.to_file(output_path, driver="GPKG", engine='pyogrio')
        print(f"✅ 병합 완료: {output_path} (총 객체 수: {len(merged_gdf)})")
        return True

    except Exception as e:
        print(f"❌ 병합 중 오류 발생: {e}")
        return False


def ShpEncoding(input_path, target_encoding='utf-8'):
    """
    [#GIS #인코딩변환 #ShpEncoding #CPG기반 #무손실 #SHP_최적화]
    기능: SHP 파일의 인코딩을 지능적으로 감지하여 사용자가 지정한 코드로 일괄 변경합니다.

    주요 특징:
        1. [CPG 기반 감지]: .cpg 파일을 우선 참조하여 현재 인코딩을 파악, 한글 깨짐 없이 데이터를 로드합니다.
        2. [속성 구조 재구성]: 단순 텍스트 수정이 아닌 DBF 파일의 바이너리 구조를 지정된 인코딩에 맞게 다시 씁니다.
        3. [CPG 강제 최적화]: 기존 내용을 삭제하고 'UTF-8' 등 지정된 인코딩명만 남도록 CPG 파일을 새로 작성합니다.
        4. [2026-01-01 무손실]: 데이터 변환 과정에서 소수점 및 좌표 정밀도를 100% 유지합니다.

    매개변수:
        input_path (str): 대상 SHP 파일 경로 또는 SHP들이 포함된 폴더 경로.
        target_encoding (str): 변환하고자 하는 인코딩 (기본값: 'utf-8').

    사용 예시:
        J_File.ShpEncoding("./999_결과/") # 폴더 내 모든 SHP를 UTF-8로 변환
        J_File.ShpEncoding("data.shp", "cp949") # 특정 파일을 CP949로 변환
    """
    # 1. 대상 선정 (단일 파일 또는 하위 폴더를 포함한 모든 SHP 탐색)
    target_files = []
    if os.path.isdir(input_path):
        # 하위 폴더(SEC246 등) 안에 있는 모든 .shp 파일을 재귀적으로 탐색합니다.
        target_files = glob.glob(os.path.join(input_path, "**", "*.shp"), recursive=True)
    else:
        target_files = [input_path]

    if not target_files:
        print("⚠️ 처리할 SHP 파일이 없습니다.")
        return False

    success_count = 0
    for shp_path in target_files:
        abs_shp = os.path.abspath(shp_path)
        cpg_path = abs_shp.replace(".shp", ".cpg")

        # 2. 기존 CPG 확인 (파일이 있으면 해당 인코딩으로 읽기, 없으면 기본 cp949)
        current_encoding = "cp949"
        if os.path.exists(cpg_path):
            try:
                with open(cpg_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read().strip()
                    if content:
                        current_encoding = content.lower()
            except:
                pass  # 읽기 실패 시 기본값 유지

        try:
            # 3. 데이터 로드 (파악된 현재 인코딩 기준)
            # [2026-01-01 데이터 소수점에 손실이 절대 없어야 합니다.]
            gdf = gpd.read_file(abs_shp, encoding=current_encoding, engine='pyogrio')

            if gdf.empty:
                continue

            # 4. 사용자 지정 인코딩으로 재저장 (덮어쓰기)
            gdf.to_file(abs_shp, driver="ESRI Shapefile", encoding=target_encoding, engine='pyogrio')

            # 5. CPG 파일 내용 업데이트 (무조건 대문자로 깔끔하게 기록)
            with open(cpg_path, 'w', encoding='utf-8') as f:
                f.write(target_encoding.upper())

            # [2026-01-27 이중 백슬래시 적용]
            print(f"✅ 인코딩 동기화 완료 ({current_encoding} -> {target_encoding}): {abs_shp.replace('\\', '\\\\')}")
            success_count += 1

        except Exception as e:
            err_msg = str(e).replace('\\', '\\\\')
            print(f"❌ {os.path.basename(abs_shp)} 변환 실패: {err_msg}")

    return True if success_count > 0 else False

def CheckGeometry(file_path):
    """
    [#GIS #SHP #타입판별 #안전모드]
    fiona를 사용하여 엔진 충돌 없이 기하 타입을 확인합니다.
    """
    try:
        # 함수 최상단 import os 삭제 (파일 최상단에 이미 있음)
        if not os.path.exists(file_path): return "FILE_NOT_FOUND"

        with fiona.open(file_path, 'r') as src:
            if len(src) == 0: return "EMPTY"
            # 첫 번째 객체의 기하 타입 확인
            first_feat = next(iter(src))
            geom_type = first_feat['geometry']['type'].upper()

        if "POINT" in geom_type: return "POINT"
        elif "LINE" in geom_type: return "LINE"
        elif "POLYGON" in geom_type: return "POLYGON"
        return "UNKNOWN"
    except Exception as e:
        print(f"⚠️ CheckGeometry 오류: {str(e).replace('\\', '\\\\')}")
        return "ERROR"


def ValidateAndClean(file_path, output_path=None):
    """
    [#GIS #데이터정제 #IllegalArgumentException방지]
    불량 객체(좌표 부족 등)를 한 줄씩 검사하여 에러 발생 객체만 제외하고 다시 저장합니다.
    """
    if output_path is None:
        output_path = file_path

        # 🚨 [추가된 로직] 원본 CPG 파일 읽기 전용으로 인코딩 파악
    cpg_path = os.path.splitext(file_path)[0] + ".cpg"
    detected_encoding = "CP949"  # 기본값 세팅

    if os.path.exists(cpg_path):
        with open(cpg_path, 'r', encoding='utf-8', errors='ignore') as f:
            cpg_content = f.read().strip().upper()
            if "UTF-8" in cpg_content:
                detected_encoding = "UTF-8"

    try:
        ext = os.path.splitext(file_path)[1].lower()

        # 1. 로우 레벨(Fiona)에서 한 줄씩 읽으며 필터링 (판별된 인코딩 적용)
        valid_features = []
        with fiona.open(file_path, 'r', encoding=detected_encoding) as src:
            meta = src.meta
            crs = src.crs
            for feature in src:
                try:
                    # Shapely 객체로 변환 시도 (여기서 1개짜리 좌표 등은 에러 발생)
                    geom = shape(feature['geometry'])

                    if geom is None or geom.is_empty:
                        continue

                    # 물리적 최소 요건 검사
                    if "Line" in geom.geom_type:
                        # 선형인데 좌표가 2개 미만이면 무조건 제거
                        if len(list(geom.coords)) < 2: continue
                    elif "Polygon" in geom.geom_type:
                        # 면형인데 외곽선 좌표가 4개(시점=종점 포함) 미만이면 제거
                        if hasattr(geom, 'exterior') and len(list(geom.exterior.coords)) < 4:
                            continue

                    valid_features.append(feature)
                except:
                    # IllegalArgumentException 유발 객체는 여기서 자동으로 스킵됨
                    continue

        if not valid_features:
            print(f"⚠️ 유효한 데이터가 없습니다: {os.path.basename(file_path)}")
            return False

        # 2. GeoDataFrame 생성 및 정밀 수선
        gdf = gpd.GeoDataFrame.from_features(valid_features, crs=crs)
        gdf.geometry = gdf.make_valid()  # 꼬인 구조 강제 교정

        # 3. 파일 저장 (안전한 fiona 엔진 사용 + 판별된 인코딩 강제 유지)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        driver = "GPKG" if ext == '.gpkg' else "ESRI Shapefile"

        # 🚨 [수정된 로직] to_file에 encoding을 넘겨주어 CPG가 멋대로 UTF-8로 바뀌는 것을 차단
        gdf.to_file(output_path, driver=driver, engine='fiona', encoding=detected_encoding)

        # 2026-01-27 지침 준수: 경로 내 백슬래시 이중 처리
        success_msg = f"✅ 세척 성공: {os.path.basename(output_path).replace('\\', '\\\\')}"
        print(success_msg)
        return True

    except Exception as e:
        err_msg = str(e).replace('\\', '\\\\')
        print(f"❌ ValidateAndClean 치명적 오류: {err_msg}")
        return False


def SummarizeSectorsToCSV(gpkg_folder_path, sector_field_name, output_csv_path, func=0):
    """
    [#GIS #통계 #매트릭스정리 #GPKG #CSV #자동화]
    통계) GPKG 파일별 섹터별 객체수 요약 및 최대객체수, 시작번호 자동 계산 CSV 생성

    입력 항목:
        gpkg_folder_path (str): 대상 GPKG 파일들이 위치한 폴더 경로.
        sector_field_name (str): GPKG 파일 내 섹터명이 들어있는 필드명 (예: 'SECTOR_NM').
        output_csv_path (str): 결과로 저장될 CSV 파일 전체 경로.
        func (int 또는 callable, 선택): 시작번호 계산 시 추가할 여유값 또는 계산 함수
                                     (기본값 0, 예: lambda x: 10 또는 5 등)

    사용 예제:
        J_Field.SummarizeSectorsToCSV(
            gpkg_folder_path="./My_GPKG_Folder",
            sector_field_name="Sector_Name",
            output_csv_path="./Result/Sector_Object_Count.csv",
            func=300
        )
    """
    if not os.path.exists(gpkg_folder_path):
        print(f"⚠️ 폴더를 찾을 수 없습니다: {gpkg_folder_path.replace('\\', '\\\\')}")
        return False

    try:
        # 1. 폴더 내 모든 GPKG 파일 검색
        search_pattern = os.path.join(gpkg_folder_path, "*.gpkg")
        gpkg_files = glob.glob(search_pattern)

        if not gpkg_files:
            print(f"⚠️ 해당 폴더에 GPKG 파일이 존재하지 않습니다: {gpkg_folder_path}")
            return False

        print(f"🔄 총 {len(gpkg_files)}개의 GPKG 파일 분석을 시작합니다.")

        master_data = {}
        all_sectors = set()

        # 2. 각 GPKG 파일 순회하며 집계
        for file_path in gpkg_files:
            file_name = Path(file_path).stem  # 파일명1, 파일명2 ...

            try:
                layers = fiona.listlayers(file_path)
                if not layers:
                    continue
                # pyogrio 엔진을 사용하여 고속 로드 및 소수점 무손실 유지
                gdf = gpd.read_file(file_path, layer=layers[0], engine='pyogrio')

                if sector_field_name not in gdf.columns:
                    print(f"  └─ ⏭️ 건너뜀 ({file_name}): '{sector_field_name}' 필드가 없습니다.")
                    continue

                gdf[sector_field_name] = gdf[sector_field_name].astype(str).str.strip()
                counts = gdf[sector_field_name].value_counts().to_dict()

                master_data[file_name] = counts
                all_sectors.update(counts.keys())

            except Exception as ex:
                print(f"  └─ ⚠️ 파일 읽기 오류 ({file_name}): {str(ex).replace('\\', '\\\\')}")

        if not master_data:
            print("❌ 집계된 유효한 데이터가 없습니다.")
            return False

        # 3. 기본 매트릭스 데이터프레임 생성 (행: 섹터명, 열: 파일명들)
        df_result = pd.DataFrame(master_data, index=list(all_sectors)).fillna(0).astype(int)

        # 섹터명 기준으로 오름차순 정렬 (순차적 시작번호 부여를 위해 필수)
        df_result = df_result.sort_index()

        # 파일명 컬럼 목록 백업
        file_columns = list(df_result.columns)

        # 4. '최대 객체수' 계산 (각 행별 파일들 중 최댓값)
        df_result['최대 객체수'] = df_result[file_columns].max(axis=1)

        # 5. '시작번호' 순차적 누적 계산 로직 적용
        # 섹터 1 = 0, 섹터 N = 이전 섹터 시작번호 + 이전 섹터 최대 객체수 + func
        start_numbers = []
        current_start = 0

        for max_cnt in df_result['최대 객체수']:
            start_numbers.append(current_start)

            # func가 함수 형태인지 값 형태인지 판별하여 처리
            if callable(func):
                extra = func(max_cnt)
            elif isinstance(func, (int, float)):
                extra = func
            else:
                extra = 0

            current_start = current_start + max_cnt + extra

        df_result['시작번호'] = start_numbers

        # 6. 컬럼 순서 재배치: [섹터명, 파일명1, 파일명2, ..., 최대 객체수, 시작번호]
        df_result = df_result.reset_index()
        df_result = df_result.rename(columns={'index': '섹터명'})

        final_columns = ['섹터명'] + file_columns + ['최대 객체수', '시작번호']
        df_result = df_result[final_columns]

        # 7. CSV 저장 (디렉토리 자동 생성 및 utf-8-sig 인코딩)
        abs_out = os.path.abspath(output_csv_path)
        os.makedirs(os.path.dirname(abs_out), exist_ok=True)

        df_result.to_csv(abs_out, index=False, encoding='utf-8-sig')

        print(f"✅ 확장 요약 CSV 생성 완료: {abs_out.replace('\\', '\\\\')}")
        return True

    except Exception as e:
        err_msg = str(e).replace('\\', '\\\\')
        print(f"🔥 SummarizeSectorsToCSV 오류 발생: {err_msg}")
        return False


def MergeSameNameFiles(source_dir, output_dir, extension="GPKG"):
    """
    [#GIS #데이터통합 #자동화 #머지 #GPKG]
    통합) 하위 폴더들에 흩어져 있는 동일한 이름의 파일들을 모아서 하나로 병합합니다.

    입력 항목:
        source_dir (str): 탐색할 최상위 디렉토리 (예: "./103_참조선으로나누기")
        output_dir (str): 병합된 파일이 저장될 디렉토리
        extension (str): 대상 파일 확장자 (기본값 "GPKG")

    사용 예제:
        J_File.MergeSameNameFiles(
            source_dir="./103_참조선으로나누기",
            output_dir="./103_참조선으로나누기/Merged_Data",
            extension="GPKG"
        )
    """
    # 1. 하위의 모든 파일 검색 (패턴 매칭)
    search_pattern = os.path.join(source_dir, f"*/*.{extension}")
    file_list = glob.glob(search_pattern)

    if not file_list:
        print(f"⚠️ 통합할 파일을 찾지 못했습니다: {source_dir}")
        return False

    # 2. 파일 이름별로 그룹화
    merged_dict = defaultdict(list)
    for x in file_list:
        file_nm = os.path.splitext(os.path.basename(x))[0]
        merged_dict[file_nm].append(x)

    os.makedirs(output_dir, exist_ok=True)
    success_count = 0

    # 3. 그룹별 병합 수행
    for file_nm, paths in merged_dict.items():
        print(f"🔄 병합 중: {file_nm} (총 {len(paths)}개 파일)")
        gdf_list = []

        for path in paths:
            try:
                try:
                    layer_name = fiona.listlayers(path)[0]
                    gdf = gpd.read_file(path, layer=layer_name, engine='pyogrio')
                except:
                    gdf = gpd.read_file(path, engine='pyogrio')
                gdf_list.append(gdf)
            except Exception as e:
                print(f"  ⚠️ 읽기 실패 ({path}): {e}")

        if gdf_list:
            combined_gdf = pd.concat(gdf_list, ignore_index=True)
            output_file = os.path.join(output_dir, f"{file_nm}.{extension.lower()}")

            combined_gdf.to_file(output_file, layer=file_nm, driver="GPKG", engine='pyogrio')
            print(f"  ✅ 저장 완료: {output_file} (총 객체: {len(combined_gdf)}개)")
            success_count += 1

    print(f"🎉 총 {success_count}개의 마스터 파일 병합이 완료되었습니다!")
    return True


def CopyGPKG(source_path, target_path):
    """
    [설명]
    geopandas를 사용하여 원본 GPKG를 읽은 뒤,
    기존 타겟 파일을 완전히 삭제하고 새로운 단일 레이어 GPKG 파일로 생성하는 모듈입니다.
    (unrecognized option 에러를 일으키는 if_exists 인자를 제거하고 삭제 방식으로 대체했습니다.)
    """
    try:
        # 1. 대상 폴더 경로 추출 및 자동 생성
        target_dir = os.path.dirname(target_path)
        if target_dir and not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)

        # 2. 원본 파일 존재 여부 확인
        if not os.path.exists(source_path):
            print(f"❌ [에러] 원본 파일을 찾을 수 없습니다: {source_path}")
            return False

        # 3. [핵심] 기존 타겟 파일과 임시 찌꺼기(-wal, -shm)가 있다면 완전히 삭제
        for ext in ["", "-wal", "-shm"]:
            f_path = target_path + ext
            if os.path.exists(f_path):
                try:
                    os.remove(f_path)
                except Exception:
                    pass

        # 4. 원본 파일 읽기 (다중 레이어 대비 첫 번째 레이어 지정 안전장치 포함)
        try:
            layers = gpd.list_layers(source_path)
            first_layer = layers.iloc[0]['name'] if hasattr(layers, 'iloc') else layers[0][0]
            gdf = gpd.read_file(source_path, layer=first_layer)
        except Exception:
            gdf = gpd.read_file(source_path)

        # 5. 대상 파일명(확장자 제외)을 새로운 단일 레이어 이름으로 지정하여 저장
        base_name = os.path.splitext(os.path.basename(target_path))[0]

        # 잘못된 if_exists 파라미터를 제거하고 순수하게 드라이버와 레이어만 지정합니다.
        gdf.to_file(target_path, layer=base_name, driver="GPKG")

        print(f"✅ 성공: 단일 레이어 파일 생성 완료 -> {target_path}")
        return True

    except Exception as e:
        print(f"🚨 [치명적 에러 발생] 파일 생성 실패:")
        traceback.print_exc()
        return False