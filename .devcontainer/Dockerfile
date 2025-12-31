FROM dart

# Install common tooling and Python 3 (use distro packages) plus system deps required by OpenCV
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
	 curl git unzip xz-utils zip libglu1-mesa \
	 ca-certificates wget gnupg2 lsb-release \
	 python3 python3-venv python3-dev python3-pip \
	 build-essential libglib2.0-0 libsm6 libxrender1 libxext6 libgl1 \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Upgrade pip for system Python and install uvicorn/uvloop and OpenCV
RUN python3 -m pip install --upgrade setuptools wheel --break-system-packages \
 && python3 -m pip install uv --break-system-packages

RUN git clone https://github.com/flutter/flutter.git -b stable --depth 1 /flutter
ENV PATH="/flutter/bin:$PATH"
RUN flutter doctor