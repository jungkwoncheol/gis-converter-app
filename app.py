import streamlit as st
import os
import J_File

st.title("GIS 및 CAD 파일 자동 변환 서비스")
st.markdown("변환할 파일(`.shp`, `.dxf`, `.zip` 등)을 업로드하고 변환 버튼을 누르세요.")

uploaded_file = st.file_uploader("파일 업로드", type=["shp", "dxf", "zip"])

if uploaded_file is not None:
    input_path = uploaded_file.name
    with open(input_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.info(f"업로드된 파일: {input_path}")

    if st.button("변환 실행하기"):
        with st.spinner("파일 변환을 진행 중입니다..."):
            try:
                # 기존 J_File.py의 변환 함수와 연결하는 부분입니다.
                # 예: J_File.변환함수이름(input_path) 형식으로 호출하도록 수정하세요.

                # 예시 출력 파일 경로 지정 (실제 변환 결과 확장자에 맞게 수정)
                output_path = input_path.rsplit(".", 1)[0] + ".gpkg"

                # J_File 내 실행 함수 호출 (필요시 코드 수정)
                # J_File.run_conversion(input_path)

                st.success("변환이 완료되었습니다!")

                if os.path.exists(output_path):
                    with open(output_path, "rb") as file:
                        st.download_button(
                            label="결과 파일 다운로드",
                            data=file,
                            file_name=os.path.basename(output_path),
                            mime="application/octet-stream"
                        )
                else:
                    st.warning("변환은 완료되었으나 결과 파일 경로를 확인해주세요.")
            except Exception as e:
                st.error(f"변환 중 오류가 발생했습니다: {e}")