# Kidsroom

Ứng dụng Python hỗ trợ cha mẹ tổ chức việc học và thưởng thời gian sử dụng máy tính trên Windows 10/11. Giao diện tối xanh tím, điểm nhấn xanh ngọc và tiếng Việt có dấu; màn hình học hiển thị nhiệm vụ theo thẻ, các câu hỏi được chia khối rõ ràng.

## Dùng bản EXE, không cần cài Python

1. Giải nén **toàn bộ** `Kidsroom-0.1.0-Windows-x64.zip`.
2. Mở thư mục `Kidsroom`, nhấn đúp **Kidsroom.exe**.
3. Cha mẹ đặt mật khẩu và tạo đề theo hướng dẫn bên dưới.
4. Muốn thoát: vào quản lý bằng mật khẩu → **Thoát giao diện**.

Giữ nguyên file EXE và thư mục `_internal` bên cạnh nhau; không chỉ sao chép riêng EXE. Bản portable không tự cài service và không yêu cầu quyền Administrator để mở giao diện. Dữ liệu vẫn nằm trong `%LOCALAPPDATA%\Kidsroom` của tài khoản đang chạy, không nằm trong ZIP.

Bản phát hành gồm:

- `Kidsroom.exe`: giao diện học sinh và cha mẹ.
- `KidsroomService.exe`: service nền và công cụ quản lý service.
- `_internal`: Python và các thư viện đã đóng gói.
- `licenses`, `THIRD-PARTY-NOTICES.txt`: giấy phép và thông báo của thư viện đi kèm.
- `Install-Service.ps1`, `BAT-DAU.txt`, `README.md`: cài service tùy chọn và hướng dẫn.

### Cài service từ bản EXE

Không cần cài Python. Mở **PowerShell Run as Administrator**, chuyển đến thư mục đã giải nén rồi chạy:

```powershell
.\Install-Service.ps1 -ChildAccount "$env:COMPUTERNAME\hocsinh"
```

Thay `hocsinh` bằng tên tài khoản Windows Standard User của trẻ. Script sao chép toàn bộ bản EXE vào `C:\Program Files\Kidsroom`, cài service auto-start và chọn tài khoản trẻ, nhưng **chưa khởi động service**. Script từ chối ghi đè thư mục hoặc service đã tồn tại.

Nếu máy không cho chạy script PowerShell chưa ký, không cần thay đổi chính sách: dùng File Explorer sao chép toàn bộ thư mục `Kidsroom` vào Program Files (thư mục đích chưa tồn tại), rồi từ PowerShell Administrator gọi trực tiếp:

```powershell
& "C:\Program Files\Kidsroom\KidsroomService.exe" --startup auto install
& "C:\Program Files\Kidsroom\KidsroomService.exe" configure "$env:COMPUTERNAME\hocsinh"
```

Chỉ tiếp tục nếu cả hai lệnh thành công. Cách này cũng chưa khởi động service.

Trước khi khởi động lại máy, đăng nhập tài khoản trẻ, cha mẹ trực tiếp mở `C:\Program Files\Kidsroom\Kidsroom.exe` để đặt mật khẩu và cấu hình bài tập. Sau đó từ PowerShell Administrator:

```powershell
Start-Service Kidsroom
Get-Service Kidsroom
```

Dừng service rồi thoát GUI bằng mật khẩu trước khi cập nhật hoặc gỡ:

```powershell
Stop-Service Kidsroom
# Sau đó vào quản lý để thoát GUI; tiếp theo mới gỡ đăng ký:
& "C:\Program Files\Kidsroom\KidsroomService.exe" remove
```

Để cập nhật bản EXE, khi service đã dừng và mọi GUI đã thoát, sao lưu dữ liệu rồi thay **toàn bộ** bộ EXE/`_internal` bằng bản mới. Không trộn bản EXE với môi trường Python nguồn trong cùng thư mục; nếu chuyển cách cài, gỡ đăng ký service cũ trước và chọn thư mục cài phù hợp.

Bản EXE chưa ký số nên Windows có thể cảnh báo nhà phát hành chưa xác định. Không tắt antivirus/SmartScreen; chỉ sử dụng bản có nguồn gốc tin cậy và kiểm tra theo chính sách bảo mật của máy. Đây là bản Windows **x64**, chưa được thử trực tiếp trên máy Windows 10 đích.

### Tự biên dịch lại EXE

Trong thư mục mã nguồn, dùng Python 64-bit trên Windows:

```powershell
& .\.venv\Scripts\python.exe -m pip install -e ".[build]"
.\scripts\build-exe.ps1
```

Kết quả nằm trong `dist\Kidsroom` và `dist\Kidsroom-0.1.0-Windows-x64.zip`. Build dùng PyInstaller dạng thư mục để service không phải giải nén thư viện vào thư mục tạm khi chạy dưới LocalSystem.

Nếu chính sách máy chặn script PowerShell, có thể gọi trực tiếp công cụ build mà không đổi chính sách:

```powershell
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean `
    --distpath dist --workpath "build\pyinstaller" "packaging\Kidsroom.spec"
```

Lệnh trực tiếp này tạo bộ EXE/`_internal`; cần chạy thêm `& .\.venv\Scripts\python.exe scripts\bundle-notices.py dist\Kidsroom` để kèm giấy phép. Script build có thêm bước chép hướng dẫn và tạo ZIP.

Có thể kiểm tra bộ thư viện đóng gói mà không mở màn hình học thật:

```powershell
$report = Join-Path $env:TEMP "Kidsroom-check.json"
$process = Start-Process ".\dist\Kidsroom\Kidsroom.exe" `
    -ArgumentList @("--self-test", ('"' + $report + '"')) -PassThru -Wait
Get-Content -LiteralPath $report
```

Chế độ này dùng Qt offscreen và cơ sở dữ liệu tạm; không chụp desktop, không cài service hay ghi vào dữ liệu thật. Kiểm tra SCM/reboot và nhận diện phần mềm đánh máy thật vẫn cần làm riêng trên máy đích.

## Chức năng

- Màn hình học toàn màn hình, topmost, không caption/nút đóng; phủ cả các màn hình phụ, bỏ qua thao tác đóng cửa sổ thông thường.
- Quản lý bằng mật khẩu: PBKDF2-SHA256 với salt riêng, 600.000 vòng; sai 5 lần tạm khóa xác thực 60 giây. Khi mở quản lý cha mẹ, các lớp phủ được ẩn và bỏ topmost để sử dụng Windows bình thường; đóng quản lý sẽ khôi phục màn hình học topmost.
- Tạo nhiều đề theo môn học: nhiều câu trắc nghiệm, trả lời ngắn hoặc tự luận trong cùng đề; sửa và ẩn/hiện từng đề.
- Soạn đề kiểu **đề thi kèm lời giải**: mỗi câu có thể nhập thêm lời giải/đáp án mẫu (tùy chọn). Trẻ không thấy lời giải; cha mẹ thấy khi duyệt tự luận để đối chiếu bài làm.
- **Nhập đề thi từ tệp JSON** hoặc **dán trực tiếp nội dung JSON** trong tab Kho đề bài; tệp hoặc nội dung dán gồm `title`, `subject`, `minutes`, `visible` và `questions` (mỗi câu có thể kèm `solution`). Hỗ trợ cả 1 đề thi hoặc danh sách nhiều đề thi. Tự động chuyển đổi các ký hiệu lũy thừa như `2^2`, `3^2`, `3^5`, `10^4`, `2^(x+1)` thành dạng số mũ Unicode (`2²`, `3²`, `3⁵`, `10⁴`, `2ˣ⁺¹`) trước khi lưu vào database; học sinh có thể trả lời bằng cả phím `^` trên bàn phím lẫn số mũ Unicode.
- Cha mẹ có thể **xuất đề đang chọn ra tệp JSON** trong tab Kho đề bài để sao lưu hoặc chuyển sang máy khác.
- Kèm sẵn 2 đề mẫu Toán 6 (Kết nối tri thức): **Đề thi Học kì I - Đề số 1** và **Đề thi Giữa học kì I - Đề số 1**, đủ phần trắc nghiệm tự chấm và tự luận kèm lời giải chi tiết; tự thêm vào Kho đề bài ở lần khởi động đầu (chỉ một lần, xóa/ẩn không bị thêm lại).
- Khi nộp, học sinh thấy số câu trắc nghiệm/trả lời ngắn đúng trên tổng số câu trong đề. Mỗi câu tự luận có giá trị bằng một câu: số câu tự luận đã trả lời được tính là điểm tiềm năng, còn cha mẹ xác nhận khi duyệt. Bài thi đạt ngưỡng khi số câu trắc nghiệm/trả lời ngắn đúng cộng với số câu tự luận đã trả lời đạt **ít nhất một nửa tổng số câu** (làm tròn lên nếu số câu lẻ). Nếu riêng câu trắc nghiệm/trả lời ngắn đúng đã đạt ngưỡng, bài được thưởng ngay, không cần cha mẹ duyệt. Nếu cần tính câu tự luận để đạt ngưỡng, bài chờ cha mẹ duyệt; nếu vẫn chưa đủ thì không được thưởng và phải chọn đề khác trong vòng đó. Trả lời ngắn chấp nhận nhiều đáp án, chuẩn hóa Unicode, khoảng trắng và hoa/thường; **vẫn phân biệt dấu tiếng Việt**, không tự suy diễn đáp án tương đương về toán học.
- Tự luận không tự chấm bằng AI: câu trả lời tự luận chỉ cần cha mẹ duyệt khi học sinh cần câu đó để đạt ngưỡng 50%; khi câu trắc nghiệm/trả lời ngắn đã đủ ngưỡng thì được thưởng ngay. Bản chụp nội dung/đáp án/phút thưởng tại thời điểm nộp được giữ lại dù đề được sửa sau đó.
- Chọn phần mềm đánh máy `.exe` và ảnh mẫu hoàn thành. OpenCV so khớp ảnh trong vùng cửa sổ ứng dụng đã chọn, chỉ khi nó đang ở phía trước.
- Chỉ thưởng sau khi ảnh kết quả **vắng mặt rồi xuất hiện liên tiếp 3 lần**; chu kỳ quét khoảng 0,8 giây. Không thưởng lại ngay từ màn hình kết quả cũ khi vừa mở.
- Tab **Thời gian và lượt thưởng** cho phép đặt số lần thưởng tối đa mỗi ngày (0–100, mặc định 4) và thời gian mỗi lần thưởng (1–240 phút). Khi lưu, số phút này áp dụng chung cho mọi đề và bài đánh máy. Trước lần lưu đầu, các mức thưởng riêng đã có vẫn được giữ; ô thời gian chung gợi ý 15 phút.
- Trong giao diện cha mẹ có nút **Đóng chương trình** để đóng hoàn toàn ứng dụng và tắt tiến trình `Kidsroom.exe`, cùng nút **Dừng Kidsroom Service** (yêu cầu quyền quản trị qua Windows để dừng service `KidsroomService.exe` và tắt toàn bộ chương trình).
- Các mức thưởng riêng vẫn được lưu trong đề và JSON, nhưng không áp dụng sau khi lưu mức thưởng chung. Bài tự luận đã nộp giữ số phút tại thời điểm nộp; thời gian đã cấp và số lượt đã dùng không bị thay đổi.
- Mỗi đề có tối đa 2 lượt nộp trong một vòng. Nếu chưa đạt 50%, trẻ không nhận thưởng, dùng hết lượt của đề đó và phải chuyển sang đề khác. Sau khi mọi đề đang hiển thị đều được nộp đủ 2 lượt, lượt làm đề trở về 0 để bắt đầu vòng mới. Hết số lượt thưởng trong ngày thì không cấp thưởng thêm, dù vẫn còn đề.
- Thời gian thưởng hiện có được hiển thị trên màn hình học. Trẻ bấm **Sử dụng máy tính** để bắt đầu đếm giờ và mở cửa sổ **Giờ khám phá**; nếu đã hết thời gian, chương trình nhắc trẻ làm bài tập để nhận thưởng. Cửa sổ này là cửa sổ thường, không topmost để không che ứng dụng khác. Bấm **Quay lại màn hình học** sẽ dừng đồng hồ và giữ phần thời gian còn lại; phần này được cộng vào lần thưởng kế tiếp. Thời gian đã bắt đầu sử dụng được lưu trong SQLite và vẫn trôi khi máy ngủ hoặc tắt.
- Windows Service chạy nền dưới LocalSystem, giám sát mỗi 2 giây và khởi động lại giao diện nếu tiến trình kết thúc.
- Không có máy chủ, tài khoản trực tuyến hay tải ảnh/nội dung học lên mạng. Ảnh chụp dùng nhận diện chỉ tồn tại trong bộ nhớ.

## Giới hạn quan trọng

Đây là **công cụ hỗ trợ gia đình, chưa phải kiosk hay giải pháp chống can thiệp**.

1. Service không được hiển thị UI trực tiếp vì Windows cô lập Session 0. Nó chỉ mở giao diện khi **tài khoản trẻ đã đăng nhập vào phiên console**. Không có cửa sổ trên màn hình đăng nhập, màn hình UAC hay Ctrl+Alt+Del.
2. Topmost không bảo đảm ngăn Alt+Tab, Task Manager, ứng dụng topmost khác, desktop khác hay người có quyền quản trị. Việc khôi phục giao diện có độ trễ. Không vô hiệu hóa công cụ quản trị/hệ thống.
3. Dùng tài khoản **Standard User riêng cho trẻ**, tài khoản Administrator riêng cho cha mẹ. Cha mẹ phải tự thiết lập mật khẩu lần đầu trước khi giao máy.
4. SQLite nằm trong hồ sơ tài khoản trẻ; người biết kỹ thuật và có quyền sửa/xóa dữ liệu đó có thể đổi thời gian, bài tập hoặc trạng thái xác thực. Mật khẩu GUI **không** là ranh giới bảo mật của Windows. Chưa có broker lưu trạng thái đặc quyền, chống sửa đồng hồ/dữ liệu hay cơ chế phục hồi mật khẩu an toàn.
5. Nhận diện ảnh là heuristic, không chứng minh học sinh thực sự làm bài. DPI, zoom, giao diện thay đổi, app launcher mở tiến trình khác hoặc ảnh giả đều có thể làm nhận diện sai. Chưa hỗ trợ phần mềm chạy trong trình duyệt/launcher chung hoặc phần mềm chạy elevated.
6. Chỉ cấu hình một tài khoản trẻ, phiên console cục bộ; không hỗ trợ quản lý nhiều trẻ/RDP. Tạm dừng bài đánh máy khi chuyển sang bài khác, vào quản lý sau xác thực hoặc khởi động lại GUI; không tự đóng phần mềm đánh máy.
7. Trong lúc đánh máy, chuyển sang ứng dụng khác sẽ khôi phục màn hình học ở lần kiểm tra tiếp theo. Nút **Quay lại bài đánh máy** chỉ tìm cửa sổ thuộc tiến trình vừa mở; chọn đúng `.exe` của ứng dụng, không chọn updater/launcher.
8. Với bài cần cha mẹ duyệt, thưởng tự luận được cộng và tính lượt vào ngày **cha mẹ duyệt**, kể cả bài nộp từ ngày trước; vẫn phải còn lượt và đề phải có trong danh sách hiện tại. Bài chờ duyệt chưa tính là hoàn thành vòng, không thể nộp trùng trước khi được duyệt/từ chối. Đồng hồ thưởng vẫn chạy khi mở phần quản lý.

Nếu cần hạn chế chắc chắn hơn, kết hợp Windows Family Safety/chính sách tài khoản hoặc chế độ kiosk phù hợp. Không cài service đặc quyền từ thư mục mà trẻ có quyền sửa.

## Chạy thử, chưa cài service

Cần Python 64-bit 3.11–3.14 và Windows 10/11.

Tại thư mục mã nguồn, dùng PowerShell:

```powershell
py -3.14 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -e .
& .\.venv\Scripts\python.exe -m kidsroom
```

Đổi `-3.14` theo phiên bản Python đang có. Dùng bản mới của pip nếu bản cũ không tìm thấy wheel tương thích.

Lần đầu:

1. Cha mẹ đặt mật khẩu ít nhất 8 ký tự, rồi đăng nhập **Cha mẹ · Quản lý**.
2. Tab **Thời gian và lượt thưởng**: nhập số lần thưởng tối đa và số phút mỗi lần → **Lưu thiết lập thưởng**.
3. Tab **Kho đề bài** → **Tạo đề**. Đặt môn, tên; thêm từng câu, chọn loại và nhập đáp án. Trắc nghiệm đánh số đáp án đúng từ **1**; lựa chọn và đáp án ngắn nhập mỗi mục một dòng. Ô **Lời giải (tùy chọn)** dành cho lời giải/đáp án mẫu, chỉ cha mẹ thấy khi duyệt. Nút **Nhập đề từ JSON** cho phép thêm đề từ tệp JSON, hoặc có thể **dán trực tiếp nội dung JSON** vào ô nhập văn bản nhiều dòng rồi bấm **Thêm đề từ nội dung JSON**; chọn một đề rồi bấm **Xuất đề ra JSON** để lưu bản JSON của đề đó.
4. Bật **Hiển thị cho con**, lưu đề. Có thể **Hiện / Ẩn đề** sau này.
5. Tab **Đánh máy**: chọn `.exe` và ảnh mẫu → **Lưu cấu hình**.
6. Tab **Duyệt bài**: bài có câu tự luận sẽ hiện tại đây nếu học sinh cần câu tự luận để đạt ngưỡng. Chọn bài để xem câu trả lời kèm lời giải gợi ý (nếu đề có), rồi **Duyệt bài và thưởng** hoặc **Yêu cầu làm lại**. Nếu câu trắc nghiệm/trả lời ngắn đã đạt ngưỡng 50%, đề được thưởng ngay và không hiện trong tab này.
7. Đóng quản lý để trở lại màn hình học. Hai đề thi Toán 6 mẫu được tự thêm vào Kho đề bài ở lần khởi động đầu; có thể **Hiện / Ẩn đề** nếu chưa muốn dùng.

Để thoát bản chạy thử: vào quản lý bằng mật khẩu → **Thoát giao diện**. Không cần cài service để thử biên soạn và chấm đề.

### Định dạng tệp đề thi JSON

Tệp nhập qua **Nhập đề từ JSON** là JSON (UTF-8). Câu `choice` cần `choices` (2–10 mục) và `correct` (chỉ số từ **0**); câu `short` cần `accepted`; câu `essay` chỉ cần `prompt`. Mọi câu có thể kèm `solution`:

```json
{
  "title": "Đề kiểm tra 15 phút",
  "subject": "Toán 6",
  "minutes": 15,
  "visible": true,
  "questions": [
    {"kind": "choice", "prompt": "2 + 2 = ?", "choices": ["A. 3", "B. 4"],
     "correct": 1, "solution": "2 + 2 = 4. Chọn B."},
    {"kind": "essay", "prompt": "Trình bày cách tính 12 × 5.",
     "solution": "12 × 5 = 60."}
  ]
}
```

Hai đề mẫu kèm chương trình nằm trong `kidsroom/exams.py`, có thể dùng làm mẫu tham khảo nội dung.

### Giới hạn thời gian bằng số lượt và vòng bài tập

Vào **Cha mẹ · Quản lý → Thời gian và lượt thưởng**, đặt **Tổng số lần thưởng tối đa** rồi bấm **Lưu thiết lập thưởng**. Màn hình cha mẹ và màn hình học đều hiển thị số lượt đã nhận/giới hạn và vòng hiện tại.

Ví dụ cha mẹ cho hiện Toán, Văn và Anh, mỗi đề thưởng 15 phút, giới hạn 4 lần/ngày:

1. Làm Toán đúng → chơi 15 phút.
2. Hết giờ phải chọn Văn hoặc Anh; chưa được dùng lại Toán để lấy thưởng.
3. Hoàn thành hai đề còn lại, mỗi đề được chơi 15 phút.
4. Đã hết danh sách vòng đầu nên được làm lại Toán (hoặc chọn đề khác trong vòng mới) để nhận lượt thứ tư.
5. Đã nhận 4 lượt = 60 phút thưởng thì hết quyền nhận thưởng trong ngày. Sang ngày mới, lượt và tiến độ vòng tự bắt đầu lại.

- Danh sách trong ngày là các đề đang bật **Hiển thị cho con**, cộng bài đánh máy nếu đã cấu hình đầy đủ `.exe` và ảnh mẫu. Cha mẹ chọn môn bằng cách ẩn/hiện đề; chưa có lịch giao bài theo ngày tự động.
- Chỉ có một bài trong danh sách thì có thể làm lại ngay sau mỗi thời gian thưởng, đến khi hết lượt.
- Tổng phút là tổng thời gian thực tế của các lần đã thưởng; thay đổi mức chung không sửa các lần trước.
- Đặt giới hạn `0` để ngừng cấp thêm lượt. Tăng/giảm giới hạn, ẩn/hiện đề, thu hồi thời gian hoặc mở lại chương trình **không xóa** lượt đã nhận trong ngày. Giờ đã thưởng vẫn còn hiệu lực nếu không dùng nút thu hồi.
- Khi sửa danh sách giữa ngày, số lần hoàn thành từng bài được giữ lại; bài có ít lần hoàn thành hơn phải được làm trước khi tiếp tục các bài có nhiều lần hơn. Ẩn đề không xóa lượt đã nhận từ đề đó.
- Ngày được tính theo giờ địa phương của Windows; thời gian đã thưởng có thể kéo sang ngày sau. Giới hạn lượt áp dụng lúc cấp thưởng, không phải là giới hạn cứng cho mọi phút sử dụng thực tế trong ngày.
- Khi cập nhật từ bản giới hạn một lần/đề/ngày, SQLite tự nâng cấp, giữ lịch sử và thời gian thưởng; lượt cũ được tính theo ngày thực tế cấp thưởng. Nên sao lưu như hướng dẫn bên dưới trước khi cập nhật.

### Chuẩn bị ảnh hoàn thành

- Chụp thủ công phần thông báo cố định, chẳng hạn “Lesson completed”, rồi cắt chỉ giữ vùng đặc trưng. Không lấy cả desktop, điểm số hoặc thời gian thay đổi.
- Ảnh PNG/JPG/BMP, ít nhất 12×12 pixel, tối đa 8 triệu pixel; không dùng ảnh đồng màu.
- Giữ nguyên mức phóng to và DPI khi chụp mẫu/chạy phần mềm.
- Mặc định ngưỡng 0,90; có thể chỉnh 0,70–0,99. Giảm ngưỡng tăng nguy cơ thưởng nhầm.
- Khi bắt đầu luyện, cần rời màn hình kết quả cũ, làm bài mới rồi để kết quả hiện đủ khoảng 3 giây.
- Ảnh cấu hình được sao chép vào thư mục dữ liệu, nên di chuyển ảnh gốc không làm mất mẫu.

## Cài Windows Service

**Thực hiện trên máy gia đình cần quản lý, bằng PowerShell Run as Administrator.** Script không được chạy tự động khi mở ứng dụng.

### 1. Chuẩn bị

- Cài Python 64-bit 3.11–3.14 cho **All Users** bên dưới `C:\Program Files`, ví dụ `C:\Program Files\Python314\python.exe`. Không dùng Python từ Microsoft Store hoặc nằm trong hồ sơ cá nhân để chạy LocalSystem.
- Tạo/kiểm tra tài khoản Standard User riêng cho trẻ, ví dụ `TENMAY\hocsinh`.
- Chỉ dùng mã nguồn đã được cha mẹ kiểm tra. Không cho trẻ quyền ghi vào Python hệ thống, môi trường service hay thư mục cài đặt.

### 2. Cài từ mã nguồn

Trong thư mục dự án:

```powershell
.\scripts\install-service.ps1 `
    -PythonPath "C:\Program Files\Python314\python.exe" `
    -ChildAccount "$env:COMPUTERNAME\hocsinh"
```

Script tạo môi trường tại `C:\Program Files\Kidsroom\runtime`, cài bản package thường (không editable), cài service auto-start và ghi SID tài khoản trẻ vào HKLM. Script từ chối ghi đè thư mục cài đặt đã tồn tại.

Service dùng chính `python.exe` của môi trường riêng làm host SCM, nên không cần sao chép `pythonservice.exe` hoặc chạy `pywin32_postinstall` vào Python hệ thống.

**Script chưa khởi động service. Không khởi động lại máy trước khi hoàn tất thiết lập lần đầu.** Đăng nhập tài khoản trẻ, có cha mẹ trực tiếp thao tác:

```powershell
& "C:\Program Files\Kidsroom\runtime\Scripts\pythonw.exe" -I -m kidsroom
```

Thiết lập mật khẩu, đề học và ảnh mẫu. Sau đó từ PowerShell Administrator:

```powershell
Start-Service Kidsroom
Get-Service Kidsroom
```

Lần sau Windows khởi động service tự động; giao diện xuất hiện sau khi tài khoản trẻ đăng nhập. Tài khoản khác không bị phủ màn hình. Nếu đã có GUI chạy thủ công, bản do service mở sẽ chờ khóa single-instance và tiếp quản khi bản trước thoát.

### 3. Dừng, cập nhật, gỡ

Từ PowerShell Administrator:

```powershell
Stop-Service Kidsroom
```

Sau đó vào giao diện → quản lý bằng mật khẩu → **Thoát giao diện**. Dừng service không cưỡng bức đóng GUI hay ứng dụng học đang mở.

Cập nhật sau khi đã dừng service và thoát GUI:

```powershell
& "C:\Program Files\Kidsroom\runtime\Scripts\python.exe" -m pip install --upgrade .
Start-Service Kidsroom
```

Gỡ đăng ký service:

```powershell
& "C:\Program Files\Kidsroom\runtime\Scripts\python.exe" -I -m kidsroom.service remove
```

Sau khi service đã gỡ và các tiến trình đã thoát, cha mẹ có thể tự xóa đúng thư mục cài đặt nếu không cần. Không tự xóa bài tập/dữ liệu cá nhân.

Đổi tài khoản trẻ: dừng service, chạy `configure`, rồi khởi động lại:

```powershell
& "C:\Program Files\Kidsroom\runtime\Scripts\python.exe" -I -m kidsroom.service configure "$env:COMPUTERNAME\taikhoankhac"
```

Tài khoản mới có dữ liệu riêng và cần thiết lập lần đầu.

## Dữ liệu và chẩn đoán

Trong **tài khoản trẻ**:

- `%LOCALAPPDATA%\Kidsroom\data.sqlite3`: cấu hình, hash mật khẩu, đề, bài nộp và lịch sử thưởng.
- `%LOCALAPPDATA%\Kidsroom\templates`: ảnh mẫu cha mẹ đã chọn.
- `%LOCALAPPDATA%\Kidsroom\app.log`: lỗi GUI/nhận diện, xoay tối đa 3 bản sao, mỗi bản khoảng 1 MB.
- `%LOCALAPPDATA%\Kidsroom\agent.lock`: khóa phiên GUI.

Service ghi thông báo/lỗi vào **Event Viewer → Windows Logs → Application**. Nếu GUI không xuất hiện, kiểm tra service, SID tài khoản, phiên console, đường dẫn Python và lỗi khởi chạy trong Event Viewer. Không chạy service dưới tài khoản trẻ: API lấy token phiên cần LocalSystem.

Sao lưu dữ liệu bằng cách dừng service và thoát GUI trước, rồi sao chép thư mục dữ liệu của trẻ. Dữ liệu không được mã hóa; cần bảo vệ bản sao lưu như tài liệu gia đình.

## Kiến trúc

- `kidsroom/core.py`: SQLite, xác thực, chấm bài, bài chờ duyệt và cấp thưởng nguyên tử.
- `kidsroom/widgets.py`: trình soạn đề, làm bài, cấu hình và duyệt của cha mẹ.
- `kidsroom/app.py`: GUI phiên người dùng, lớp phủ nhiều màn hình, đồng hồ và single-instance.
- `kidsroom/vision.py`: OpenCV + MSS trong QThread; kiểm tra ứng dụng foreground trước khi chụp.
- `kidsroom/service.py`: host SCM, đối chiếu SID, `WTSQueryUserToken` + `CreateProcessAsUser` trên desktop `winsta0\default`. GUI chạy bằng token trẻ, **không** chạy bằng LocalSystem.
- `scripts/install-service.ps1`: cài môi trường service vào Program Files.

## Kiểm thử

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
& .\.venv\Scripts\python.exe -m compileall -q kidsroom tests
& .\.venv\Scripts\python.exe -m pip check
Remove-Item Env:\QT_QPA_PLATFORM
```

Các bài kiểm thử GUI dùng nền offscreen, không phủ desktop thật. Kiểm thử service giả lập API tạo tiến trình/token; kiểm thử ảnh dùng ảnh tổng hợp, không chụp màn hình cá nhân.

**Chưa xác nhận bằng thử nghiệm cài SCM/reboot thật hoặc phần mềm đánh máy cụ thể.** Trước khi sử dụng chính thức, cha mẹ cần kiểm tra trên máy Windows 10 đích:

1. GUI xuất hiện đúng ở tài khoản trẻ, không xuất hiện ở tài khoản cha mẹ.
2. Kết thúc đúng tiến trình GUI trong phiên thử: service mở lại trong khoảng vài giây.
3. Hoàn thành bài đánh máy thực tế: chỉ kết quả mới được thưởng; chuyển sang app khác khôi phục màn hình học.
4. Tạo đề thưởng 1 phút, làm đúng, chờ hết phút: màn hình học phủ lại toàn bộ màn hình.
5. Trong lúc còn thời gian thưởng, khởi động lại GUI/Windows: không được đặt lại thành 15 phút.
6. Thử sai mật khẩu, ẩn đề, duyệt/từ chối tự luận, rút/cắm màn hình phụ và dừng/gỡ service bằng Administrator.
