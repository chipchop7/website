# モジュール宣言/変数初期化
use strict;
my %cf;
#┌─────────────────────────────────
#│ ASKA BBS : init.cgi - 2022/03/10
#│ copyright (c) kentweb, 1997-2022
#│ https://www.kent-web.com/
#└─────────────────────────────────
$cf{version} = 'ASKA BBS v8.22';
#┌─────────────────────────────────
#│ [注意事項]
#│ 1. このプログラムはフリーソフトです。このプログラムを使用した
#│    いかなる損害に対して作者は一切の責任を負いません。
#│ 2. 設置に関する質問はサポート掲示板にお願いいたします。
#│    直接メールによる質問は一切お受けいたしておりません。
#└─────────────────────────────────

#===========================================================
# ■ 基本設定
#===========================================================

# 掲示板タイトル
$cf{bbs_title} = '掲示板 - Aska BBS';

# 本体プログラムURL【URLパス】
$cf{bbs_cgi} = './aska.cgi';

# 管理プログラムURL【URLパス】
$cf{admin_cgi} = './admin.cgi';

# データディレクトリ【サーバパス】
$cf{datadir} = './data';

# テンプレートディレクトリ【サーバパス】
$cf{tmpldir} = './tmpl';

# 共通ディレクトリ【URLパス】
$cf{cmnurl} = './cmn';

# 最大記事数（これを超える記事は古い順に削除）
$cf{maxlog} = 100;

# １ページあたりの記事表示件数
$cf{pg_max} = 10;

# 戻り先URL【URLパス】
$cf{homepage} = "../First.html";

# URLの自動リンク (0=no 1=yes)
$cf{autolink} = 1;

# 引用部色変更
#  1 : 色指定を行うと「引用部」を色変更します
#  2 : この機能を使用しない場合は何も記述しない
$cf{ref_col} = "#0000a0";

# メール通知機能
# → 0=no  1=yes
$cf{mailing} = 0;

# メール通知先アドレス（メール通知する場合）
$cf{mailto} = 'xxx@xxx.xx';

# sendmailのパス（メール通知する場合）
$cf{sendmail} = '/usr/lib/sendmail';

# sendmailの -fコマンドが必要な場合
# 0=no 1=yes
$cf{sendm_f} = 0;

# 記事の更新は method=post に限定する場合（セキュリティ対策）
#  → 0=no 1=yes
$cf{postonly} = 1;

# 同一IPからの連続投稿制限（秒数で指定する）
$cf{wait_time} = 60;

# 禁止ワード
# → 投稿時禁止するワードをコンマで区切る
$cf{no_wd} = '';

# 日本語チェック（投稿時日本語が含まれていなければ拒否する）
# 0=No  1=Yes
$cf{jp_wd} = 1;

# URL個数チェック
# → 投稿コメント中に含まれるURL個数の最大値
$cf{urlnum} = 1;

# アクセス制限（半角スペースで区切る、アスタリスク可）
#  → 拒否ホスト名を記述（後方一致）【例】*.anonymizer.com
$cf{deny_host} = '';
#  → 拒否IPアドレスを記述（前方一致）【例】210.12.345.*
$cf{deny_addr} = '';

# １回当りの最大投稿サイズ (bytes)
$cf{maxdata} = 51200;

# ホスト取得方法
# 0 : gethostbyaddr関数を使わない
# 1 : gethostbyaddr関数を使う
$cf{gethostbyaddr} = 0;

# クッキーID名（特に変更しなくてよい）
# → クッキー保存名
$cf{cookie_id} = "askabbs";

# 管理パスワードの最大間違い制限
# → この回数以上パスワードを間違うとロックします
$cf{max_failpass} = 5;

# 管理パスワードのロック期間：自動解除を日数で指定
# → この値を 0 にすると自動解除しません。
$cf{lock_days} = 14;

# -------------------------------------------------------------- #
# [ 以下は「画像認証機能」機能（スパム対策）を使用する場合の設定 ]
#
# 画像認証機能の使用
# 0 : しない
# 1 : ライブラリ版（pngren.pl）
# 2 : モジュール版（GD::SecurityImage + Image::Magick）→ Image::Magick必須
$cf{use_captcha} = 1;

# 認証用画像生成ファイル【URLパス】
$cf{captcha_cgi} = './captcha.cgi';

# 画像認証プログラム【サーバパス】
$cf{captsec_pl} = './lib/captsec.pl';
$cf{pngren_pl}  = './lib/pngren.pl';

# 投稿キー許容時間（分単位）
# → 投稿フォーム表示後、送信ボタンが押されるまでの可能時間。
$cf{cap_time} = 30;

# 投稿キーの文字数
# ライブラリ版 : 4～8文字で設定
# モジュール版 : 6～8文字で設定
$cf{cap_len} = 6;

# 画像/フォント格納ディレクトリ【サーバパス】
$cf{bin_dir} = './lib/bin';

# [ライブラリ版] 画像ファイル [ ファイル名のみ ]
$cf{si_png} = "br3.png";

# [モジュール版] 画像フォント [ ファイル名のみ ]
$cf{font_ttl} = "redressed.ttf";

#===========================================================
# ■ 設定完了
#===========================================================

# 設定値を返す
sub set_init { return %cf; }

#-----------------------------------------------------------
#  フォームデコード
#-----------------------------------------------------------
sub parse_form {
	my ($buf,%in);
	if ($ENV{REQUEST_METHOD} eq "POST") {
		error('受理できません') if ($ENV{CONTENT_LENGTH} > $cf{maxdata});
		read(STDIN,$buf,$ENV{CONTENT_LENGTH});
	} else {
		$buf = $ENV{QUERY_STRING};
	}
	foreach ( split(/&/,$buf) ) {
		my ($key,$val) = split(/=/);
		$key =~ tr/+/ /;
		$key =~ s/%([a-fA-F0-9][a-fA-F0-9])/pack("H2", $1)/eg;
		$val =~ tr/+/ /;
		$val =~ s/%([a-fA-F0-9][a-fA-F0-9])/pack("H2", $1)/eg;
		
		# 無効化
		$val =~ s/&/&amp;/g;
		$val =~ s/</&lt;/g;
		$val =~ s/>/&gt;/g;
		$val =~ s/"/&quot;/g;
		$val =~ s/'/&#39;/g;
		$val =~ s|\r\n|<br>|g;
		$val =~ s|[\r\n]|<br>|g;
		
		$in{$key} .= "\0" if (defined $in{$key});
		$in{$key} .= $val;
	}
	return %in;
}


1;

