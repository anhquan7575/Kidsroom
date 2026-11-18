"""De thi mau dong goi kem chuong trinh.

Moi phan tu cua BUNDLED_EXAMS la (slug, exam) voi slug dung de tranh
nhap trung khi khoi dong lai. Noi dung de va loi giai giu nguyen tieng
Viet co dau nhu de goc.
"""

EXAM_HOC_KI_1 = {
    "title": "Đề thi Học kì I - Toán 6 Kết nối tri thức (Đề số 1)",
    "subject": "Toán 6",
    "minutes": 30,
    "visible": True,
    "questions": [
        {
            "kind": "choice",
            "prompt": "Phần I - Trắc nghiệm. Câu 1. Cách viết nào sau đây là đúng?",
            "choices": ["A. 3,2 ∈ N", "B. 0 ∈ N*", "C. 0 ∈ N", "D. 0 ∉ N"],
            "correct": 2,
            "solution": "Phương pháp: N = {0; 1; 2; ...} là tập hợp các số tự nhiên; "
                        "N* là tập hợp các số tự nhiên khác 0.\n"
                        "Cách giải: 3,2 là số thập phân nên không thuộc N; 0 không thuộc N*; "
                        "0 thuộc N. Chọn C.",
        },
        {
            "kind": "choice",
            "prompt": "Câu 2. Trong các số sau, số nào chia hết cho cả 2; 3; 5 và 9?",
            "choices": ["A. 39595", "B. 39590", "C. 39690", "D. 39592"],
            "correct": 2,
            "solution": "Phương pháp: Số chia hết cho cả 2 và 5 có tận cùng là 0; "
                        "số có tổng các chữ số chia hết cho 9 thì chia hết cho 9 (và cho 3).\n"
                        "Cách giải: 39690 tận cùng là 0 nên chia hết cho 2 và 5; "
                        "3 + 9 + 6 + 9 + 0 = 27 chia hết cho 9 nên cũng chia hết cho 3 và 9. Chọn C.",
        },
        {
            "kind": "choice",
            "prompt": "Câu 3. Kết quả của phép tính 3^15 : 9^3 là:",
            "choices": ["A. 3^9", "B. 3^12", "C. 3^18", "D. 3^21"],
            "correct": 0,
            "solution": "Phương pháp: Đưa về cùng cơ số rồi áp dụng a^m : a^n = a^(m-n).\n"
                        "Cách giải: 9^3 = (3^2)^3 = 3^6 nên 3^15 : 9^3 = 3^15 : 3^6 = 3^9. Chọn A.",
        },
        {
            "kind": "choice",
            "prompt": "Câu 4. Tìm số nguyên x biết x - (-199) = -1.",
            "choices": ["A. x = 198", "B. x = -200", "C. x = 200", "D. x = -198"],
            "correct": 1,
            "solution": "Phương pháp: Muốn tìm số bị trừ, lấy hiệu cộng với số trừ.\n"
                        "Cách giải: x = -1 + (-199) = -200. Chọn B.",
        },
        {
            "kind": "choice",
            "prompt": "Câu 5. Kết quả của phép tính nào sau đây là số nguyên tố?",
            "choices": ["A. 5^3 - 5^2", "B. 4^2 - 3^2", "C. 6^2 - 3^2", "D. 5^2 - 3^2"],
            "correct": 1,
            "solution": "Phương pháp: Tính từng kết quả rồi kiểm tra tính nguyên tố.\n"
                        "Cách giải: 5^3 - 5^2 = 100; 4^2 - 3^2 = 7 là số nguyên tố; "
                        "6^2 - 3^2 = 27; 5^2 - 3^2 = 16. Chọn B.",
        },
        {
            "kind": "choice",
            "prompt": "Câu 6. Khẳng định nào sau đây KHÔNG đúng?",
            "choices": ["A. 6 > 5", "B. -6 < -5", "C. 6 > -5", "D. -6 > -5"],
            "correct": 3,
            "solution": "Phương pháp: Trong hai số nguyên âm, số nào có phần số tự nhiên "
                        "lớn hơn thì nhỏ hơn.\n"
                        "Cách giải: -6 < -5 nên khẳng định -6 > -5 là sai. Chọn D.",
        },
        {
            "kind": "choice",
            "prompt": "Câu 7. Một hình vuông có cạnh 10 cm. Chu vi hình vuông đó là:",
            "choices": ["A. 40 cm", "B. 40 cm²", "C. 100 cm", "D. 100 cm²"],
            "correct": 0,
            "solution": "Phương pháp: Chu vi hình vuông bằng 4 lần độ dài cạnh.\n"
                        "Cách giải: 4 × 10 = 40 (cm). Chú ý đơn vị chu vi là cm, "
                        "không phải cm². Chọn A.",
        },
        {
            "kind": "choice",
            "prompt": "Câu 8. Hiên nhà có dạng hình thang với hai đáy 14 m và 36 m, chiều cao "
                      "12 m. Người ta lát gạch toàn bộ hiên với giá 120 000 đồng/m². "
                      "Tổng chi phí lát gạch là:",
            "choices": ["A. 7 440 000 đồng", "B. 144 000 000 đồng",
                        "C. 36 000 000 đồng", "D. 72 000 000 đồng"],
            "correct": 2,
            "solution": "Phương pháp: Diện tích hình thang = (đáy lớn + đáy nhỏ) × chiều cao : 2; "
                        "chi phí = diện tích × đơn giá.\n"
                        "Cách giải: S = (14 + 36) × 12 : 2 = 300 (m²). "
                        "Chi phí = 300 × 120 000 = 36 000 000 (đồng). Chọn C.",
        },
        {
            "kind": "choice",
            "prompt": "Câu 9. Trong bốn hình sau, hình nào có diện tích bé nhất?\n"
                      "Hình 1: hình vuông cạnh 4 cm.\n"
                      "Hình 2: hình bình hành đáy 5 cm, chiều cao 2 cm.\n"
                      "Hình 3: hình chữ nhật 4 cm × 3 cm.\n"
                      "Hình 4: hình thoi có hai đường chéo 6 cm và 3 cm.",
            "choices": ["A. Hình 1", "B. Hình 2", "C. Hình 3", "D. Hình 4"],
            "correct": 3,
            "solution": "Phương pháp: Tính diện tích từng hình rồi so sánh.\n"
                        "Cách giải: Hình 1: 4 × 4 = 16 cm²; Hình 2: 5 × 2 = 10 cm²; "
                        "Hình 3: 4 × 3 = 12 cm²; Hình 4: 6 × 3 : 2 = 9 cm². "
                        "Hình 4 bé nhất. Chọn D.",
        },
        {
            "kind": "choice",
            "prompt": "Câu 10. Hình chữ nhật (không phải hình vuông) có bao nhiêu trục đối xứng?",
            "choices": ["A. 1", "B. 2", "C. 3", "D. 4"],
            "correct": 1,
            "solution": "Phương pháp: Trục đối xứng của hình chữ nhật là hai đường thẳng đi qua "
                        "trung điểm của từng cặp cạnh đối diện.\n"
                        "Cách giải: Hình chữ nhật có 2 trục đối xứng. Chọn B.",
        },
        {
            "kind": "essay",
            "prompt": "Phần II - Tự luận. Bài 1 (1,5 điểm). Thực hiện phép tính:\n"
                      "a) 12 : [450 : (125 + 25 × 4)]\n"
                      "b) 4 × 5² - 3² × (2015⁰ + 1¹⁰⁰)\n"
                      "c) 98 × 12345 + 12345 × 101 + 12345",
            "solution": "Phương pháp: Tính trong ngoặc trước, lũy thừa trước nhân chia; "
                        "câu c dùng tính chất phân phối.\n"
                        "Cách giải:\n"
                        "a) 12 : [450 : (125 + 100)] = 12 : (450 : 225) = 12 : 2 = 6.\n"
                        "b) 4 × 25 - 9 × (1 + 1) = 100 - 18 = 82.\n"
                        "c) 12345 × (98 + 101 + 1) = 12345 × 200 = 2 469 000.",
        },
        {
            "kind": "essay",
            "prompt": "Bài 2 (1 điểm). Tìm số tự nhiên x, biết:\n"
                      "a) 71 - (33 + x) = 26\n"
                      "b) 3^(4x+1) = 27^(x+3)",
            "solution": "Phương pháp: a) Tìm số trừ rồi tìm x. "
                        "b) Đưa về cùng cơ số 3 rồi cho hai số mũ bằng nhau.\n"
                        "Cách giải:\n"
                        "a) 33 + x = 71 - 26 = 45 nên x = 45 - 33 = 12.\n"
                        "b) 27^(x+3) = 3^(3x+9) nên 4x + 1 = 3x + 9, suy ra x = 8.",
        },
        {
            "kind": "essay",
            "prompt": "Bài 3 (1 điểm).\n"
                      "a) Tìm số tự nhiên x lớn nhất sao cho 480 ⋮ x và 600 ⋮ x.\n"
                      "b) Tìm các số tự nhiên x sao cho x ⋮ 20, x ⋮ 35 và x < 500.",
            "solution": "Phương pháp: a) Số lớn nhất mà cả hai số cùng chia hết là ƯCLN. "
                        "b) x chia hết cho cả 20 và 35 nên x là bội chung của chúng.\n"
                        "Cách giải:\n"
                        "a) 480 = 2^5 × 3 × 5; 600 = 2^3 × 3 × 5². "
                        "ƯCLN(480, 600) = 2^3 × 3 × 5 = 120. Vậy x = 120.\n"
                        "b) BCNN(20, 35) = 140 nên BC(20, 35) = {0; 140; 280; 420; 560; ...}. "
                        "Vì x < 500 nên x ∈ {0; 140; 280; 420}.",
        },
        {
            "kind": "essay",
            "prompt": "Bài 4 (2 điểm). Một mảnh đất gồm hình bình hành ABCD và hình thang cân "
                      "BEFC ghép lại (BC là cạnh chung). Hình bình hành ABCD có AD = 40 m, "
                      "DC = 44 m, chiều cao ứng với cạnh AD là DM = 41 m. Hình thang cân BEFC "
                      "có hai đáy BC = 40 m, EF = 24 m, chiều cao EN = 42 m và hai cạnh bên "
                      "BE = CF = 45 m.\n"
                      "a) Tính diện tích mảnh đất.\n"
                      "b) Tính chu vi mảnh đất (đường bao gồm các cạnh AB, AD, DC, CF, FE, EB).",
            "solution": "Phương pháp: Diện tích hình bình hành = đáy × chiều cao; diện tích "
                        "hình thang = (tổng hai đáy) × chiều cao : 2; chu vi là tổng các cạnh "
                        "bao quanh mảnh đất.\n"
                        "Cách giải:\n"
                        "a) S(ABCD) = 40 × 41 = 1640 (m²); "
                        "S(BEFC) = (40 + 24) × 42 : 2 = 1344 (m²). "
                        "Diện tích mảnh đất: 1640 + 1344 = 2984 (m²).\n"
                        "b) Chu vi = DC + CF + FE + EB + BA + AD "
                        "= 44 + 45 + 24 + 45 + 44 + 40 = 242 (m).",
        },
        {
            "kind": "essay",
            "prompt": "Bài 5 (0,5 điểm). Cho A = 1 + 3 + 3² + 3³ + ... + 3¹¹. "
                      "Chứng minh rằng A chia hết cho 13.",
            "solution": "Phương pháp: Nhóm 3 số hạng liên tiếp để xuất hiện thừa số 13.\n"
                        "Cách giải: A = (1 + 3 + 3²) + (3³ + 3⁴ + 3⁵) + (3⁶ + 3⁷ + 3⁸) + "
                        "(3⁹ + 3¹⁰ + 3¹¹) = 13 + 3³ × 13 + 3⁶ × 13 + 3⁹ × 13 "
                        "= 13 × (1 + 3³ + 3⁶ + 3⁹). Vậy A ⋮ 13 (điều phải chứng minh).",
        },
    ],
}

EXAM_GIUA_HOC_KI_1 = {
    "title": "Đề thi Giữa học kì I - Toán 6 Kết nối tri thức (Đề số 1)",
    "subject": "Toán 6",
    "minutes": 30,
    "visible": True,
    "questions": [
        {
            "kind": "choice",
            "prompt": "Phần I - Trắc nghiệm. Câu 1. Tháng nào sau đây KHÔNG có 31 ngày?",
            "choices": ["A. Tháng 5", "B. Tháng 6", "C. Tháng 7", "D. Tháng 8"],
            "correct": 1,
            "solution": "Phương pháp: Nhớ số ngày của các tháng trong năm.\n"
                        "Cách giải: Tháng 5, 7, 8 có 31 ngày; tháng 6 chỉ có 30 ngày. Chọn B.",
        },
        {
            "kind": "choice",
            "prompt": "Câu 2. Tập hợp các chữ cái xuất hiện trong cụm từ \"TOÁN 6\" là:",
            "choices": ["A. {T; O; A; N; 6}", "B. {T; O; A; N}",
                        "C. {T; O; N}", "D. {T; A; N}"],
            "correct": 1,
            "solution": "Phương pháp: Liệt kê các chữ cái, mỗi phần tử chỉ viết một lần; "
                        "số 6 không phải chữ cái.\n"
                        "Cách giải: Các chữ cái là T, O, A, N nên tập hợp là {T; O; A; N}. Chọn B.",
        },
        {
            "kind": "choice",
            "prompt": "Câu 3. Tìm số tự nhiên x biết 2^(x+1) × 2² = 16.",
            "choices": ["A. x = 4", "B. x = 3", "C. x = 2", "D. x = 1"],
            "correct": 3,
            "solution": "Phương pháp: Áp dụng a^m × a^n = a^(m+n) rồi so sánh số mũ.\n"
                        "Cách giải: 2^(x+1+2) = 2^4 nên x + 3 = 4, suy ra x = 1. Chọn D.",
        },
        {
            "kind": "choice",
            "prompt": "Câu 4. Tập hợp các ước của 6 là:",
            "choices": ["A. {0; 1; 2; 3; 6}", "B. {1; 2; 3}",
                        "C. {2; 3; 6}", "D. {1; 2; 3; 6}"],
            "correct": 3,
            "solution": "Phương pháp: Ước của 6 là các số tự nhiên mà 6 chia hết.\n"
                        "Cách giải: Ư(6) = {1; 2; 3; 6}. Chọn D.",
        },
        {
            "kind": "choice",
            "prompt": "Câu 5. Nếu a ⋮ 3, b ⋮ 3 và c ⋮ 3 thì:",
            "choices": ["A. (a + b + c) ⋮ 3", "B. (a + b + c) ⋮ 9",
                        "C. (a + b + c) ⋮ 27", "D. (a + b + c) không chia hết cho 3"],
            "correct": 0,
            "solution": "Phương pháp: Tính chất chia hết của một tổng: các số hạng cùng chia "
                        "hết cho m thì tổng chia hết cho m.\n"
                        "Cách giải: a, b, c đều chia hết cho 3 nên (a + b + c) ⋮ 3. Chọn A.",
        },
        {
            "kind": "choice",
            "prompt": "Câu 6. Số 27 được viết bằng chữ số La Mã là:",
            "choices": ["A. XVII", "B. XXV", "C. XXVI", "D. XXVII"],
            "correct": 3,
            "solution": "Phương pháp: X = 10, V = 5, I = 1.\n"
                        "Cách giải: 27 = 10 + 10 + 5 + 1 + 1 = XXVII. Chọn D.",
        },
        {
            "kind": "choice",
            "prompt": "Câu 7. Cho số M = 1a7b (a, b là chữ số). Biết M chia hết cho cả 2; 5 và 9. "
                      "Khi đó:",
            "choices": ["A. a = 0, b = 1", "B. a = 1, b = 0",
                        "C. a = 2, b = 0", "D. a = 1, b = 5"],
            "correct": 1,
            "solution": "Phương pháp: Chia hết cho cả 2 và 5 thì tận cùng là 0; chia hết cho 9 "
                        "thì tổng các chữ số chia hết cho 9.\n"
                        "Cách giải: b = 0; khi đó 1 + a + 7 + 0 = 8 + a ⋮ 9 nên a = 1. Chọn B.",
        },
        {
            "kind": "choice",
            "prompt": "Câu 8. Tam giác đều MNP có MN = 7 cm. Khi đó:",
            "choices": ["A. NP = MP = 5 cm", "B. NP = 7 cm; MP = 5 cm",
                        "C. NP = MP = 7 cm", "D. NP = MP = 14 cm"],
            "correct": 2,
            "solution": "Phương pháp: Tam giác đều có ba cạnh bằng nhau.\n"
                        "Cách giải: NP = MP = MN = 7 cm. Chọn C.",
        },
        {
            "kind": "choice",
            "prompt": "Câu 9. Khẳng định nào sau đây SAI khi nói về hình thoi?",
            "choices": ["A. Bốn cạnh bằng nhau",
                        "B. Hai đường chéo vuông góc với nhau",
                        "C. Hai đường chéo bằng nhau",
                        "D. Các cạnh đối song song với nhau"],
            "correct": 2,
            "solution": "Phương pháp: Nhớ các tính chất của hình thoi.\n"
                        "Cách giải: Hai đường chéo của hình thoi vuông góc nhưng nói chung "
                        "không bằng nhau. Chọn C.",
        },
        {
            "kind": "choice",
            "prompt": "Câu 10. Cho hình bình hành ABCD. Khẳng định nào sau đây SAI?",
            "choices": ["A. AB = CD", "B. AD = BC", "C. AB song song với CD", "D. AC = BD"],
            "correct": 3,
            "solution": "Phương pháp: Hình bình hành có các cạnh đối bằng nhau và song song; "
                        "hai đường chéo nói chung không bằng nhau.\n"
                        "Cách giải: AC = BD chỉ đúng với hình chữ nhật. Chọn D.",
        },
        {
            "kind": "choice",
            "prompt": "Câu 11. Một hình chữ nhật có diện tích 96 cm² và một cạnh dài 12 cm. "
                      "Chu vi hình chữ nhật đó là:",
            "choices": ["A. 20 cm", "B. 40 cm", "C. 48 cm", "D. 80 cm"],
            "correct": 1,
            "solution": "Phương pháp: Cạnh còn lại = diện tích : cạnh đã biết; "
                        "chu vi = 2 × (dài + rộng).\n"
                        "Cách giải: Cạnh còn lại: 96 : 12 = 8 (cm). "
                        "Chu vi: 2 × (12 + 8) = 40 (cm). Chọn B.",
        },
        {
            "kind": "choice",
            "prompt": "Câu 12. Một lục giác đều được ghép từ 6 tam giác đều có cạnh 6 cm. "
                      "Độ dài đường chéo chính của lục giác đều đó là:",
            "choices": ["A. 12 cm", "B. 18 cm", "C. 24 cm", "D. 36 cm"],
            "correct": 0,
            "solution": "Phương pháp: Đường chéo chính của lục giác đều bằng 2 lần cạnh.\n"
                        "Cách giải: 2 × 6 = 12 (cm). Chọn A.",
        },
        {
            "kind": "essay",
            "prompt": "Phần II - Tự luận. Bài 1 (1 điểm). Viết các tập hợp sau bằng cách "
                      "liệt kê phần tử:\n"
                      "a) Tập hợp B các số tự nhiên lớn hơn 9 và nhỏ hơn 12.\n"
                      "b) Tập hợp C các số tự nhiên chẵn nhỏ hơn 10.",
            "solution": "Phương pháp: Liệt kê các phần tử thỏa mãn điều kiện, mỗi phần tử "
                        "viết một lần.\n"
                        "Cách giải:\n"
                        "a) B = {10; 11}.\n"
                        "b) C = {0; 2; 4; 6; 8}.",
        },
        {
            "kind": "essay",
            "prompt": "Bài 2 (1 điểm). Thực hiện phép tính (tính hợp lý nếu có thể):\n"
                      "a) 237 + 86 + 63 + 214\n"
                      "b) 45 + [32 - (4 + 3 × 5)]\n"
                      "c) 5 × 25 × 2 × 16 × 4\n"
                      "d) 10⁴ : [4 × (5² - 5)] + 25",
            "solution": "Phương pháp: Nhóm các số có tổng/tích tròn; thực hiện trong ngoặc "
                        "trước, lũy thừa trước nhân chia.\n"
                        "Cách giải:\n"
                        "a) (237 + 63) + (86 + 214) = 300 + 300 = 600.\n"
                        "b) 45 + [32 - (4 + 15)] = 45 + (32 - 19) = 45 + 13 = 58.\n"
                        "c) (5 × 2) × (25 × 4) × 16 = 10 × 100 × 16 = 16 000.\n"
                        "d) 10 000 : [4 × (25 - 5)] + 25 = 10 000 : 80 + 25 = 125 + 25 = 150.",
        },
        {
            "kind": "essay",
            "prompt": "Bài 3 (1 điểm). Tìm số tự nhiên x, biết:\n"
                      "a) (x - 45) × 27 = 0\n"
                      "b) 3x - 2⁴ = 5³",
            "solution": "Phương pháp: a) Tích bằng 0 mà 27 ≠ 0 nên thừa số kia bằng 0. "
                        "b) Tính các lũy thừa rồi tìm x.\n"
                        "Cách giải:\n"
                        "a) x - 45 = 0 nên x = 45.\n"
                        "b) 3x - 16 = 125 nên 3x = 141, suy ra x = 47.",
        },
        {
            "kind": "essay",
            "prompt": "Bài 4 (1 điểm). Không thực hiện phép tính, xét xem các tổng (hiệu) sau "
                      "có chia hết cho 2 không, có chia hết cho 5 không?\n"
                      "a) 125 + 360\n"
                      "b) 2 × 3 × 4 × 5 × 6 + 82\n"
                      "c) 2 × 3 × 4 × 5 × 6 - 95",
            "solution": "Phương pháp: Dùng tính chất chia hết của tổng và hiệu.\n"
                        "Cách giải:\n"
                        "a) 125 ⋮ 5 và 360 ⋮ 5 nên tổng chia hết cho 5; 125 là số lẻ nên tổng "
                        "không chia hết cho 2.\n"
                        "b) Tích 2 × 3 × 4 × 5 × 6 chia hết cho cả 2 và 5; 82 ⋮ 2 nên tổng chia "
                        "hết cho 2; 82 không chia hết cho 5 nên tổng không chia hết cho 5.\n"
                        "c) 95 ⋮ 5 nên hiệu chia hết cho 5; 95 là số lẻ nên hiệu không chia "
                        "hết cho 2.",
        },
        {
            "kind": "essay",
            "prompt": "Bài 5 (1 điểm). Bạn Lan có 50 000 đồng, mua 8 quyển vở và 5 chiếc bút, "
                      "mỗi chiếc bút giá 2 000 đồng, sau khi mua còn thừa 8 000 đồng. "
                      "Hỏi giá tiền mỗi quyển vở là bao nhiêu?",
            "solution": "Phương pháp: Tính tổng tiền đã mua, trừ tiền bút rồi chia cho số vở.\n"
                        "Cách giải: Số tiền mua hàng: 50 000 - 8 000 = 42 000 (đồng). "
                        "Tiền mua bút: 5 × 2 000 = 10 000 (đồng). "
                        "Tiền mua vở: 42 000 - 10 000 = 32 000 (đồng). "
                        "Giá mỗi quyển vở: 32 000 : 8 = 4 000 (đồng).",
        },
        {
            "kind": "essay",
            "prompt": "Bài 6 (1 điểm). Vẽ hình chữ nhật ABCD có AB = 5 cm, BC = 3 cm.\n"
                      "a) Nêu các cặp cạnh bằng nhau của hình chữ nhật ABCD.\n"
                      "b) Tính chu vi và diện tích của hình chữ nhật ABCD.",
            "solution": "Phương pháp: Hình chữ nhật có các cạnh đối bằng nhau; "
                        "chu vi = 2 × (dài + rộng); diện tích = dài × rộng.\n"
                        "Cách giải:\n"
                        "a) AB = CD = 5 cm; BC = AD = 3 cm.\n"
                        "b) Chu vi: 2 × (5 + 3) = 16 (cm). Diện tích: 5 × 3 = 15 (cm²).",
        },
        {
            "kind": "essay",
            "prompt": "Bài 7 (1 điểm). Cho hình chữ nhật ABCD ghép với hình vuông BEFC "
                      "(BC là cạnh chung), biết AB = 4 cm và BE = 3 cm. "
                      "Tính diện tích hình chữ nhật ABCD.",
            "solution": "Phương pháp: Hình vuông có bốn cạnh bằng nhau nên BC = BE; "
                        "diện tích hình chữ nhật = dài × rộng.\n"
                        "Cách giải: BEFC là hình vuông nên BC = BE = 3 cm. "
                        "Diện tích hình chữ nhật ABCD: 4 × 3 = 12 (cm²).",
        },
    ],
}

BUNDLED_EXAMS = [
    ("toan6-knnt-hoc-ki-1-de-1", EXAM_HOC_KI_1),
    ("toan6-knnt-giua-hoc-ki-1-de-1", EXAM_GIUA_HOC_KI_1),
]
